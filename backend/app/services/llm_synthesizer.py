"""LLM 통합 호출 — insights / improvements 합성 (SPEC §7-3 #4).

5축 카테고리 모듈이 ``analyze()`` 로 메트릭만 반환하면, 이 모듈이 통합 LLM 호출
한 번으로 자연어 insights와 improvements 리스트를 생성한다.

Phase 1 G3: **더미 구현**. Claude API 호출 ❌, 메트릭 fail 패턴에서 결정적 규칙
기반 stub 생성. 라우터/태스크 흐름 검증과 프론트엔드 mock 데이터 공급이 목적.

Phase 1 후속 / Phase 2: 실 ``anthropic.AsyncAnthropic`` 호출로 대체.
``app.scoring.v1.visibility`` 가 호출 패턴 참고용.

설계 메모:
    - 입력은 ``CategoryMetrics`` 리스트(분석된 카테고리만 포함, partial 허용).
    - 출력: ``insights`` (lang→string) + ``improvements`` (List[Improvement]).
    - lang 은 워크스페이스 ``primary_language`` (en/ko/es) 직접 전달.
    - 실패 메트릭 우선순위 = weight 큰 것 먼저 (영향도 높음).
    - i18n 사전 키 ``scoring.{cat}.{metric_key}.improvement_title`` 컨벤션.
"""
from __future__ import annotations

from typing import Any

from app.scoring.schemas import (
    CategoryMetrics,
    CategoryName,
    Improvement,
    ImprovementEffort,
    ImprovementPriority,
    MetricResult,
)


_PRIORITY_BY_RANK: tuple[ImprovementPriority, ...] = ("high", "medium", "low")
_EFFORT_BY_WEIGHT: tuple[tuple[float, ImprovementEffort], ...] = (
    # (weight 임계값 이상 → effort)
    (0.25, "high"),
    (0.15, "medium"),
    (0.0,  "low"),
)


def _improvement_for_metric(
    category: CategoryName,
    metric: MetricResult,
    rank: int,
) -> Improvement:
    """단일 fail 메트릭 → Improvement (stub).

    rank: 0이 가장 영향도 큰 fail (priority=high). 3 이상은 low.
    """
    priority: ImprovementPriority = (
        _PRIORITY_BY_RANK[rank] if rank < len(_PRIORITY_BY_RANK) else "low"
    )
    effort: ImprovementEffort = next(
        eff for thr, eff in _EFFORT_BY_WEIGHT if metric.weight >= thr
    )
    # Phase 1 더미 — 실제 LLM 통합 시 lang→설명을 동적 생성.
    desc_template = (
        f"[stub G3] Metric '{metric.key}' failed. "
        f"This is a placeholder improvement; real LLM-generated guidance comes in a later chunk."
    )
    return Improvement(
        priority=priority,
        category=category,
        title_key=f"scoring.{category}.{metric.key}.improvement_title",
        description={
            "en": desc_template,
            "ko": f"[stub G3] '{metric.key}' 메트릭 통과 ❌. 실제 개선 제안은 후속 청크에서 LLM 통합 호출로 채움.",
            "es": f"[stub G3] La métrica '{metric.key}' no pasó. Sugerencia LLM real pendiente.",
        },
        # impact 1~10. weight(0~1) × 10을 반올림, 최소 1.
        estimated_impact=max(1, min(10, round(metric.weight * 10))),
        estimated_effort=effort,
        related_metric_keys=[metric.key],
    )


def _summary_text(category_results: dict[CategoryName, CategoryMetrics]) -> dict[str, str]:
    """카테고리별 점수 요약 — lang(en/ko/es) → 1줄 텍스트.

    Phase 1 더미 — 실제 LLM 통합 시 자연어 요약 생성.
    """
    if not category_results:
        return {"en": "No categories analyzed.", "ko": "분석된 카테고리가 없습니다.", "es": "No se analizaron categorías."}
    parts = ", ".join(
        f"{cat}={cm.score:.0f}" for cat, cm in category_results.items()
    )
    return {
        "en": f"[stub G3] Category scores: {parts}.",
        "ko": f"[stub G3] 카테고리 점수: {parts}.",
        "es": f"[stub G3] Puntuaciones por categoría: {parts}.",
    }


async def synthesize(
    category_results: dict[CategoryName, CategoryMetrics],
    *,
    primary_language: str = "en",
    max_improvements: int = 10,
) -> tuple[dict[str, Any], list[Improvement]]:
    """카테고리 결과 → (insights JSONB, improvements 리스트).

    insights 스키마 (analysis_results.insights JSONB):
        {
          "summary": { "en": "...", "ko": "...", "es": "..." },
          "primary_language": "en",
          "synthesized_by": "stub-v0",
          "category_count": 5
        }

    improvements 리스트 (analysis_results.improvements JSONB는 list[dict] 직렬화):
        - 각 카테고리에서 fail 메트릭을 weight 내림차순 → 상위 N개 stub Improvement.
        - 분석 결과 raw_metrics 와 related_metric_keys 로 UI 연결.
    """
    # 카테고리 순서는 입력 dict 순서 유지(Python 3.7+ insertion order).
    fail_candidates: list[tuple[CategoryName, MetricResult]] = []
    for cat, cm in category_results.items():
        for m in cm.metrics:
            if not m.passed:
                fail_candidates.append((cat, m))

    # weight 내림차순 정렬 → priority/effort 매핑이 의미있도록.
    fail_candidates.sort(key=lambda t: t[1].weight, reverse=True)

    improvements: list[Improvement] = [
        _improvement_for_metric(cat, m, rank=idx)
        for idx, (cat, m) in enumerate(fail_candidates[:max_improvements])
    ]

    insights: dict[str, Any] = {
        "summary": _summary_text(category_results),
        "primary_language": primary_language,
        "synthesized_by": "stub-v0",
        "category_count": len(category_results),
    }
    return insights, improvements
