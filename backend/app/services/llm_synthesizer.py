"""LLM 통합 호출 — insights / improvements 합성 (SPEC §7-3 #4).

5축 카테고리 모듈이 ``analyze()`` 로 메트릭만 반환하면, 이 모듈이 통합 LLM 호출
한 번으로 자연어 insights와 multilingual improvements 리스트를 생성한다.

Phase 1 G6 (2026-05-03):
    - Claude Sonnet 4.6 단일 호출 (``settings.synthesizer_model``).
    - Anthropic ``tool_use`` + ``tool_choice`` 강제 → Pydantic 검증.
    - multilingual output (en/ko/es) 1번 호출에 동시 생성 → 비용 1x.
    - LLM 실패/api_key 없음 → 결정적 stub fallback (``synthesized_by=stub-fallback``).
    - High priority cap: LLM 이 자유 결정한 priority 중 high 가 cap 을 초과하면
      낮은 impact 부터 medium 으로 강등 (UI 노이즈 방지).

설계 메모:
    - Improvement.title_key 는 LLM 생성 ❌ — metric key 에서 deterministic 도출.
      `scoring.{cat}.{metric_key}.improvement_title` 컨벤션 (i18n 사전 키).
    - related_metric_keys 는 단일 메트릭으로 강제 (UI 1:1 매핑 + i18n 키 단순화).
    - tool_use input_schema 의 metric_keys / categories enum 으로 LLM 의 임의 키 생성 차단.
    - synthesized_by 값:
        - "{model_id}" — LLM 호출 성공 (예: "claude-sonnet-4-6")
        - "stub-fallback" — LLM 실패 / api_key 없음 / 빈 입력
"""
from __future__ import annotations

import logging
from typing import Any

import anthropic
from pydantic import ValidationError

from app.config import get_settings
from app.scoring.schemas import (
    ALL_CATEGORIES,
    CategoryMetrics,
    CategoryName,
    Improvement,
    ImprovementEffort,
    ImprovementPriority,
    MetricResult,
)


log = logging.getLogger(__name__)


# ─── 상수 (이 모듈 단일 소스) ────────────────────────────────────────────

SYNTHESIZER_MAX_TOKENS: int = 4096
HIGH_PRIORITY_CAP: int = 3
# Synthesizer LLM 출력 lang. **profiles/workspaces 의 20 lang ENUM 과 별개:**
# F-i18n-1 시점에 ENUM 은 20 lang 으로 확장됐지만, synth 출력은 Phase 3 까지 3 lang.
# workspace.primary_language='fr' 같은 경우 synth 는 'en/ko/es' 키만 채움 → email_service 가
# `summary_obj.get(lang) or summary_obj.get('en')` 으로 graceful degrade. Phase 3 청크에서
# 20 lang 으로 확장 + 비용/품질 검토.
SUPPORTED_LANGUAGES: tuple[str, ...] = ("en", "ko", "es")
TOOL_NAME: str = "produce_synthesis"

# stub fallback (LLM 호출 ❌) 에서 priority 매핑 — weight 내림차순 rank 기준.
_STUB_PRIORITY_BY_RANK: tuple[ImprovementPriority, ...] = ("high", "medium", "low")
_STUB_EFFORT_BY_WEIGHT: tuple[tuple[float, ImprovementEffort], ...] = (
    (0.25, "high"),
    (0.15, "medium"),
    (0.0,  "low"),
)


# ─── stub fallback (deterministic) ──────────────────────────────────────

def _stub_improvement(
    category: CategoryName, metric: MetricResult, rank: int,
) -> Improvement:
    priority: ImprovementPriority = (
        _STUB_PRIORITY_BY_RANK[rank]
        if rank < len(_STUB_PRIORITY_BY_RANK) else "low"
    )
    effort: ImprovementEffort = next(
        eff for thr, eff in _STUB_EFFORT_BY_WEIGHT if metric.weight >= thr
    )
    return Improvement(
        priority=priority,
        category=category,
        title_key=f"scoring.{category}.{metric.key}.improvement_title",
        description={
            "en": (
                f"[stub-fallback] Metric '{metric.key}' did not pass. "
                f"LLM synthesis unavailable; deterministic placeholder shown."
            ),
            "ko": (
                f"[stub-fallback] '{metric.key}' 메트릭 통과 ❌. "
                f"LLM 합성 사용 불가 — 결정적 placeholder 로 표시."
            ),
            "es": (
                f"[stub-fallback] La métrica '{metric.key}' no pasó. "
                f"Síntesis LLM no disponible; se muestra placeholder determinista."
            ),
        },
        estimated_impact=max(1, min(10, round(metric.weight * 10))),
        estimated_effort=effort,
        related_metric_keys=[metric.key],
    )


def _stub_summary(
    category_results: dict[CategoryName, CategoryMetrics],
) -> dict[str, str]:
    if not category_results:
        return {
            "en": "No categories analyzed.",
            "ko": "분석된 카테고리가 없습니다.",
            "es": "No se analizaron categorías.",
        }
    parts = ", ".join(
        f"{cat}={cm.score:.0f}" for cat, cm in category_results.items()
    )
    return {
        "en": f"[stub-fallback] Category scores: {parts}.",
        "ko": f"[stub-fallback] 카테고리 점수: {parts}.",
        "es": f"[stub-fallback] Puntuaciones por categoría: {parts}.",
    }


def _synthesize_stub(
    category_results: dict[CategoryName, CategoryMetrics],
    primary_language: str,
    max_improvements: int,
    *,
    fallback_reason: str,
) -> tuple[dict[str, Any], list[Improvement]]:
    """결정적 stub — LLM 호출 ❌. fail 메트릭 weight 내림차순 → 상위 N."""
    fail_candidates: list[tuple[CategoryName, MetricResult]] = []
    for cat, cm in category_results.items():
        for m in cm.metrics:
            if not m.passed:
                fail_candidates.append((cat, m))
    fail_candidates.sort(key=lambda t: t[1].weight, reverse=True)

    improvements = [
        _stub_improvement(cat, m, rank=idx)
        for idx, (cat, m) in enumerate(fail_candidates[:max_improvements])
    ]
    insights: dict[str, Any] = {
        "summary": _stub_summary(category_results),
        "primary_language": primary_language,
        "synthesized_by": "stub-fallback",
        "fallback_reason": fallback_reason,
        "category_count": len(category_results),
    }
    return insights, improvements


# ─── tool_use schema + prompt ────────────────────────────────────────────

def _multilingual_string_schema(description: str) -> dict[str, Any]:
    """en/ko/es 3 언어 동시 생성 강제 — 모든 언어 required string."""
    return {
        "type": "object",
        "description": description,
        "properties": {
            lang: {"type": "string", "minLength": 1}
            for lang in SUPPORTED_LANGUAGES
        },
        "required": list(SUPPORTED_LANGUAGES),
        "additionalProperties": False,
    }


def _build_tool_input_schema(
    metric_keys: list[str],
    categories: list[str],
    max_improvements: int,
) -> dict[str, Any]:
    """tool_use input_schema — Improvement multilingual + LLM 결정 필드만.

    title_key 는 schema 에서 ❌ (metric key 에서 우리가 deterministic 도출).
    related_metric_keys 는 정확히 1개로 강제 (1:1 매핑).
    """
    return {
        "type": "object",
        "properties": {
            "summary": _multilingual_string_schema(
                "Holistic 2-3 sentence summary of the analysis in each language."
            ),
            "improvements": {
                "type": "array",
                "minItems": 0,
                "maxItems": max_improvements,
                "description": (
                    f"Up to {max_improvements} prioritized improvements. "
                    f"At most {HIGH_PRIORITY_CAP} may be 'high' priority."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "priority": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                        },
                        "category": {
                            "type": "string",
                            "enum": categories,
                        },
                        "description": _multilingual_string_schema(
                            "2-3 sentence improvement description in each language."
                        ),
                        "estimated_impact": {
                            "type": "integer", "minimum": 1, "maximum": 10,
                        },
                        "estimated_effort": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                        },
                        "related_metric_keys": {
                            "type": "array",
                            "minItems": 1, "maxItems": 1,
                            "items": {"type": "string", "enum": metric_keys},
                        },
                    },
                    "required": [
                        "priority", "category", "description",
                        "estimated_impact", "estimated_effort",
                        "related_metric_keys",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["summary", "improvements"],
        "additionalProperties": False,
    }


def _format_metrics_for_prompt(
    category_results: dict[CategoryName, CategoryMetrics],
) -> str:
    """LLM 에 전달할 메트릭 요약 텍스트.

    fail 우선 + pass 컨텍스트. evidence 포함 (디버그 가능 + 근거 있는 제안).
    """
    lines: list[str] = []
    for cat, cm in category_results.items():
        lines.append(f"\n## Category: {cat} (score={cm.score:.1f}/100)")
        fails = [m for m in cm.metrics if not m.passed]
        passes = [m for m in cm.metrics if m.passed]
        if fails:
            lines.append("Failed metrics (priority focus):")
            for m in fails:
                ev = (m.evidence or "")[:120]
                lines.append(
                    f"  - [{m.key}] weight={m.weight:.2f} "
                    f"value={m.value} threshold={m.threshold} evidence={ev}"
                )
        if passes:
            lines.append("Passed metrics (context):")
            for m in passes:
                lines.append(f"  - [{m.key}] weight={m.weight:.2f} value={m.value}")
    return "\n".join(lines)


def _build_prompt(
    category_results: dict[CategoryName, CategoryMetrics],
    primary_language: str,
    max_improvements: int,
) -> str:
    metrics_block = _format_metrics_for_prompt(category_results)
    return f"""You are an AEO (AI Engine Optimization) expert. Analyze the website scoring \
results below and produce structured output via the `{TOOL_NAME}` tool.

The user's primary language is: {primary_language} (en/ko/es supported).

Scoring breakdown (5 categories: technical/structured/content/authority/visibility):
{metrics_block}

Your task:
1. `summary`: Holistic 2-3 sentence summary in en/ko/es. Include the strongest \
category and the weakest, and the most impactful next step.
2. `improvements`: Up to {max_improvements} prioritized improvements. Focus on \
failed metrics first. Each improvement must:
   - Reference exactly ONE metric in `related_metric_keys` (no grouping).
   - Have multilingual `description` (en/ko/es), 2-3 sentences each, concrete \
and actionable. Reference the metric's evidence when relevant.
   - Have `priority` (high/medium/low). At most {HIGH_PRIORITY_CAP} may be 'high'.
   - Have `estimated_impact` (1-10 integer) and `estimated_effort` (low/medium/high).

Be specific to the metric's evidence — no generic advice. Use the user's domain \
context implicit in the metrics. Produce ONLY the tool call, no other text."""


# ─── tool_use 응답 파싱 + 검증 ───────────────────────────────────────────

def _extract_tool_input(response: Any) -> dict[str, Any] | None:
    """messages.create() 응답에서 tool_use block 의 input dict 추출."""
    content = getattr(response, "content", None) or []
    for block in content:
        if getattr(block, "type", None) == "tool_use":
            inp = getattr(block, "input", None)
            if isinstance(inp, dict):
                return inp
    return None


def _cap_high_priority(
    improvements: list[Improvement], *, cap: int = HIGH_PRIORITY_CAP,
) -> list[Improvement]:
    """high 가 cap 초과 시 impact 낮은 것부터 medium 으로 강등."""
    highs = [(i, imp) for i, imp in enumerate(improvements) if imp.priority == "high"]
    if len(highs) <= cap:
        return improvements
    # impact 오름차순 → 작은 것부터 강등 (impact 큰 것이 high 유지).
    highs.sort(key=lambda t: t[1].estimated_impact)
    demote_count = len(highs) - cap
    demote_indices = {idx for idx, _ in highs[:demote_count]}

    new_list: list[Improvement] = []
    for idx, imp in enumerate(improvements):
        if idx in demote_indices:
            new_list.append(imp.model_copy(update={"priority": "medium"}))
        else:
            new_list.append(imp)
    return new_list


def _build_improvement(
    raw: dict[str, Any], category_keys: set[str],
) -> Improvement | None:
    """LLM tool_use item → Improvement (검증 + title_key 도출).

    실패 시 None (호출자가 skip).
    """
    related = raw.get("related_metric_keys") or []
    if not isinstance(related, list) or len(related) != 1:
        log.warning("Improvement skipped: related_metric_keys must be length 1, got %r", related)
        return None
    metric_key = related[0]

    category = raw.get("category")
    if category not in category_keys:
        log.warning(
            "Improvement skipped: category=%r not in analyzed set=%s",
            category, sorted(category_keys),
        )
        return None

    title_key = f"scoring.{category}.{metric_key}.improvement_title"
    try:
        return Improvement(
            priority=raw["priority"],
            category=category,
            title_key=title_key,
            description=raw["description"],
            estimated_impact=raw["estimated_impact"],
            estimated_effort=raw["estimated_effort"],
            related_metric_keys=[metric_key],
        )
    except (KeyError, ValidationError) as exc:
        log.warning("Improvement skipped: validation failed (%s) raw=%r", exc, raw)
        return None


# ─── main entry ─────────────────────────────────────────────────────────

async def synthesize(
    category_results: dict[CategoryName, CategoryMetrics],
    *,
    primary_language: str = "en",
    max_improvements: int = 10,
) -> tuple[dict[str, Any], list[Improvement]]:
    """카테고리 결과 → (insights JSONB, improvements 리스트).

    Phase 1 G6: Claude Sonnet 4.6 (``settings.synthesizer_model``) tool_use 호출.
    실패 시 stub fallback (synthesized_by="stub-fallback").

    insights 스키마 (analysis_results.insights JSONB):
        성공 ─ {
          "summary": {"en": "...", "ko": "...", "es": "..."},
          "primary_language": "en",
          "synthesized_by": "{model_id}",
          "category_count": 5,
          "improvements_count": 8,
          "high_priority_capped": false
        }
        fallback ─ {
          ...,
          "synthesized_by": "stub-fallback",
          "fallback_reason": "..."
        }
    """
    # 0) 빈 입력 방어 — analysis_task 가 사전 검증하지만 안전망.
    if not category_results:
        return _synthesize_stub(
            category_results, primary_language, max_improvements,
            fallback_reason="empty_category_results",
        )

    # 1) 설정 로드 + api key 확인.
    settings = get_settings()
    api_key = getattr(settings, "claude_api_key", None)
    model = getattr(settings, "synthesizer_model", "claude-sonnet-4-6")
    if not api_key:
        log.warning("synthesizer: no claude_api_key, using stub fallback")
        return _synthesize_stub(
            category_results, primary_language, max_improvements,
            fallback_reason="no_api_key",
        )

    # 2) 분석된 카테고리 / 메트릭 키 enum 추출.
    categories = list(category_results.keys())
    metric_keys = sorted({
        m.key for cm in category_results.values() for m in cm.metrics
    })
    if not metric_keys:
        # 카테고리 있는데 메트릭 0개 — 비정상. stub.
        return _synthesize_stub(
            category_results, primary_language, max_improvements,
            fallback_reason="no_metrics_in_categories",
        )

    # 3) tool_use schema + prompt 생성.
    tool_schema = _build_tool_input_schema(
        metric_keys=metric_keys,
        categories=[str(c) for c in categories],
        max_improvements=max_improvements,
    )
    prompt = _build_prompt(category_results, primary_language, max_improvements)

    # 4) LLM 호출 (tool_choice 강제).
    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=model,
            max_tokens=SYNTHESIZER_MAX_TOKENS,
            tools=[{
                "name": TOOL_NAME,
                "description": (
                    "Produce multilingual insights summary and prioritized "
                    "improvements list from the analysis results."
                ),
                "input_schema": tool_schema,
            }],
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("synthesizer: LLM call failed (%s), using stub fallback", exc)
        return _synthesize_stub(
            category_results, primary_language, max_improvements,
            fallback_reason=f"llm_call_error: {str(exc)[:120]}",
        )

    # 5) tool_use block 추출.
    tool_input = _extract_tool_input(response)
    if tool_input is None:
        log.warning("synthesizer: response missing tool_use block, using stub")
        return _synthesize_stub(
            category_results, primary_language, max_improvements,
            fallback_reason="missing_tool_use_block",
        )

    # 6) summary 검증.
    summary_raw = tool_input.get("summary") or {}
    if not all(
        isinstance(summary_raw.get(lang), str) and summary_raw[lang]
        for lang in SUPPORTED_LANGUAGES
    ):
        log.warning(
            "synthesizer: summary missing required langs (%s), using stub",
            SUPPORTED_LANGUAGES,
        )
        return _synthesize_stub(
            category_results, primary_language, max_improvements,
            fallback_reason="invalid_summary_multilingual",
        )
    summary = {lang: summary_raw[lang] for lang in SUPPORTED_LANGUAGES}

    # 7) improvements 검증 + Improvement 변환.
    raw_imps = tool_input.get("improvements") or []
    if not isinstance(raw_imps, list):
        raw_imps = []
    category_keys = {str(c) for c in ALL_CATEGORIES}
    improvements: list[Improvement] = []
    for raw in raw_imps[:max_improvements]:
        if not isinstance(raw, dict):
            continue
        imp = _build_improvement(raw, category_keys)
        if imp is not None:
            improvements.append(imp)

    # 8) high priority cap.
    pre_cap_high = sum(1 for imp in improvements if imp.priority == "high")
    improvements = _cap_high_priority(improvements, cap=HIGH_PRIORITY_CAP)
    capped = pre_cap_high > HIGH_PRIORITY_CAP

    # 9) insights 조립.
    insights: dict[str, Any] = {
        "summary": summary,
        "primary_language": primary_language,
        "synthesized_by": model,
        "category_count": len(category_results),
        "improvements_count": len(improvements),
        "high_priority_capped": capped,
    }
    return insights, improvements
