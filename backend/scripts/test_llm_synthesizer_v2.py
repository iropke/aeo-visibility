"""LLM Synthesizer 단위 테스트 (G6, services/llm_synthesizer).

실행:
    Set-Location backend; $env:PYTHONUTF8="1"; $env:PYTHONPATH="$PWD"
    .venv\\Scripts\\python.exe scripts\\test_llm_synthesizer_v2.py

검증:
- happy path: tool_use 응답 → multilingual summary + Improvement 리스트.
- fallback 분기: api_key 없음 / LLM 예외 / tool_use block 누락 / 빈 입력.
- High priority cap (>3 → impact 작은 high 가 medium 으로 강등).
- Improvement 검증: invalid category / related_metric_keys 길이 ≠ 1 → skip.
- title_key 가 metric key 에서 deterministic 도출 (LLM 결정 ❌).

mock 패턴 (test_visibility_v2.py 와 동일):
- anthropic.AsyncAnthropic → MagicMock(return_value=mock_client) 로 교체.
- mock_client.messages.create → AsyncMock(return_value=mock_response).
- get_settings → monkey-patch 로 claude_api_key + synthesizer_model 시뮬레이션.
"""
from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.scoring.schemas import (
    CategoryMetrics, CategoryName, MetricResult,
)
from app.services import llm_synthesizer as synth_mod
from app.services.llm_synthesizer import (
    HIGH_PRIORITY_CAP,
    SUPPORTED_LANGUAGES,
    TOOL_NAME,
    _build_improvement,
    _build_prompt,
    _build_tool_input_schema,
    _cap_high_priority,
    _extract_tool_input,
    _stub_summary,
    _synthesize_stub,
    synthesize,
)


# ─── 픽스처 ─────────────────────────────────────────────────────────────

def _metric(
    key: str, weight: float, *, passed: bool, value=None, evidence: str = ""
) -> MetricResult:
    return MetricResult(
        key=key,
        display_name_key=f"scoring.test.{key}.display",
        description_key=f"scoring.test.{key}.description",
        value=value,
        weight=weight,
        passed=passed,
        threshold=None,
        evidence=evidence,
    )


def _category(score: float, metrics: list[MetricResult]) -> CategoryMetrics:
    return CategoryMetrics(score=score, metrics=metrics)


def _sample_results() -> dict[CategoryName, CategoryMetrics]:
    """5축 중 2축 분석 — fail 메트릭 4 + pass 1."""
    return {
        "technical": _category(
            score=33.3,
            metrics=[
                _metric("ssl_enabled", 0.50, passed=False, value=False, evidence="https failed"),
                _metric("robots_txt_ok", 0.30, passed=True, value=True),
                _metric("sitemap_ok", 0.20, passed=False, value=False, evidence="404"),
            ],
        ),
        "content": _category(
            score=20.0,
            metrics=[
                _metric("readability", 0.60, passed=False, value=42, evidence="below 60"),
                _metric("freshness_days", 0.40, passed=False, value=200, evidence="stale"),
            ],
        ),
    }


def _make_tool_use_response(tool_input: dict) -> MagicMock:
    """anthropic Message 응답 mock — content[0].type='tool_use'."""
    block = MagicMock()
    block.type = "tool_use"
    block.input = tool_input
    return MagicMock(content=[block])


def _make_anthropic_client(create_side_effect) -> MagicMock:
    client = MagicMock()
    if isinstance(create_side_effect, list):
        client.messages.create = AsyncMock(side_effect=create_side_effect)
    else:
        client.messages.create = AsyncMock(return_value=create_side_effect)
    return client


def _patch_anthropic(client: MagicMock):
    synth_mod.anthropic.AsyncAnthropic = MagicMock(return_value=client)


def _restore_anthropic(original):
    synth_mod.anthropic.AsyncAnthropic = original


def _patch_settings(api_key: str | None, model: str = "claude-sonnet-4-6"):
    fake = SimpleNamespace(claude_api_key=api_key, synthesizer_model=model)
    synth_mod.get_settings = lambda: fake


def _multi(en: str = "en text", ko: str = "ko 텍스트", es: str = "es texto") -> dict[str, str]:
    return {"en": en, "ko": ko, "es": es}


def _imp_dict(
    *,
    priority: str = "medium",
    category: str = "technical",
    metric_key: str = "ssl_enabled",
    impact: int = 7,
    effort: str = "medium",
    description: dict[str, str] | None = None,
) -> dict:
    return {
        "priority": priority,
        "category": category,
        "description": description or _multi(),
        "estimated_impact": impact,
        "estimated_effort": effort,
        "related_metric_keys": [metric_key],
    }


FAILED: list[str] = []


def _check(label: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    suffix = f" — {detail}" if detail and not cond else ""
    print(f"  [{status}] {label}{suffix}")
    if not cond:
        FAILED.append(label)


# ─── 헬퍼 단위 테스트 ─────────────────────────────────────────────────

def test_build_tool_input_schema():
    print("\n== _build_tool_input_schema ==")
    schema = _build_tool_input_schema(
        metric_keys=["ssl_enabled", "readability"],
        categories=["technical", "content"],
        max_improvements=10,
    )
    _check("T01 schema is object with summary+improvements required",
           schema["type"] == "object"
           and set(schema["required"]) == {"summary", "improvements"})

    summary_schema = schema["properties"]["summary"]
    _check("T02 summary requires en/ko/es",
           set(summary_schema["required"]) == set(SUPPORTED_LANGUAGES))

    item_schema = schema["properties"]["improvements"]["items"]
    _check("T03 improvement category is enum-restricted",
           item_schema["properties"]["category"]["enum"] == ["technical", "content"])
    _check("T04 related_metric_keys is array length=1 with enum",
           item_schema["properties"]["related_metric_keys"]["minItems"] == 1
           and item_schema["properties"]["related_metric_keys"]["maxItems"] == 1
           and item_schema["properties"]["related_metric_keys"]["items"]["enum"] == ["ssl_enabled", "readability"])
    _check("T05 maxItems on improvements = max_improvements",
           schema["properties"]["improvements"]["maxItems"] == 10)


def test_build_prompt():
    print("\n== _build_prompt ==")
    results = _sample_results()
    prompt = _build_prompt(results, "ko", 10)
    _check("T06 prompt mentions tool name",
           TOOL_NAME in prompt)
    _check("T07 prompt mentions primary language",
           "ko" in prompt and "en/ko/es" in prompt)
    _check("T08 prompt includes failed metric evidence",
           "ssl_enabled" in prompt and "https failed" in prompt
           and "readability" in prompt and "below 60" in prompt)
    _check("T09 prompt includes passed metric as context",
           "robots_txt_ok" in prompt)
    _check("T10 prompt mentions HIGH cap",
           str(HIGH_PRIORITY_CAP) in prompt)


def test_extract_tool_input():
    print("\n== _extract_tool_input ==")
    inp = {"summary": _multi(), "improvements": []}
    resp = _make_tool_use_response(inp)
    _check("T11 extract from tool_use block",
           _extract_tool_input(resp) == inp)

    # 다른 블록 타입 mix
    text_block = MagicMock(); text_block.type = "text"
    tool_block = MagicMock(); tool_block.type = "tool_use"; tool_block.input = inp
    resp2 = MagicMock(content=[text_block, tool_block])
    _check("T12 extract tool_use among mixed blocks",
           _extract_tool_input(resp2) == inp)

    # 누락
    resp3 = MagicMock(content=[text_block])
    _check("T13 missing tool_use → None",
           _extract_tool_input(resp3) is None)

    # input 이 dict 아님
    bad_block = MagicMock(); bad_block.type = "tool_use"; bad_block.input = "not a dict"
    resp4 = MagicMock(content=[bad_block])
    _check("T14 non-dict input → None",
           _extract_tool_input(resp4) is None)


def test_build_improvement():
    print("\n== _build_improvement ==")
    cat_keys = {"technical", "structured", "content", "authority", "visibility"}

    # 정상
    raw = _imp_dict(category="technical", metric_key="ssl_enabled")
    imp = _build_improvement(raw, cat_keys)
    _check("T15 valid → Improvement with deterministic title_key",
           imp is not None
           and imp.title_key == "scoring.technical.ssl_enabled.improvement_title")
    _check("T16 related_metric_keys preserved (length 1)",
           imp.related_metric_keys == ["ssl_enabled"])

    # related_metric_keys 길이 != 1
    raw_bad = _imp_dict()
    raw_bad["related_metric_keys"] = ["a", "b"]
    _check("T17 related_metric_keys length != 1 → skip",
           _build_improvement(raw_bad, cat_keys) is None)
    raw_bad["related_metric_keys"] = []
    _check("T18 empty related_metric_keys → skip",
           _build_improvement(raw_bad, cat_keys) is None)

    # invalid category
    raw_bad_cat = _imp_dict(category="bogus")
    _check("T19 invalid category → skip",
           _build_improvement(raw_bad_cat, cat_keys) is None)

    # invalid priority (Pydantic Literal violation)
    raw_bad_prio = _imp_dict(priority="urgent")
    _check("T20 invalid priority → skip",
           _build_improvement(raw_bad_prio, cat_keys) is None)

    # invalid impact
    raw_bad_impact = _imp_dict(impact=15)
    _check("T21 estimated_impact > 10 → skip",
           _build_improvement(raw_bad_impact, cat_keys) is None)

    # 누락 키
    raw_missing = _imp_dict()
    del raw_missing["description"]
    _check("T22 missing required field → skip",
           _build_improvement(raw_missing, cat_keys) is None)


def test_cap_high_priority():
    print("\n== _cap_high_priority ==")
    cat_keys = {"technical", "content"}
    base = lambda prio, impact, key="ssl_enabled": _build_improvement(
        _imp_dict(priority=prio, impact=impact, metric_key=key), cat_keys
    )
    # 4 high + 1 medium → 1 강등 (impact 작은 것)
    imps = [
        base("high", 9, "ssl_enabled"),
        base("high", 5, "readability"),
        base("high", 8, "freshness_days"),
        base("high", 3, "sitemap_ok"),  # 가장 작음 → demote
        base("medium", 7),
    ]
    capped = _cap_high_priority(imps, cap=HIGH_PRIORITY_CAP)
    high_count = sum(1 for i in capped if i.priority == "high")
    _check(f"T23 4 highs (cap={HIGH_PRIORITY_CAP}) → cap to 3",
           high_count == HIGH_PRIORITY_CAP)
    # 가장 impact 낮은 high (impact=3) 가 demoted 되어야 함
    demoted = [i for i in capped if i.estimated_impact == 3 and i.priority == "medium"]
    _check("T24 lowest-impact high demoted to medium", len(demoted) == 1)

    # 3 이하면 변경 ❌
    imps3 = [base("high", 9), base("high", 5), base("medium", 4)]
    no_change = _cap_high_priority(imps3, cap=HIGH_PRIORITY_CAP)
    _check("T25 ≤ cap → no change",
           sum(1 for i in no_change if i.priority == "high") == 2)


# ─── stub fallback ──────────────────────────────────────────────────────

def test_stub_summary():
    print("\n== _stub_summary ==")
    s = _stub_summary({})
    _check("T26 empty results → all 3 langs filled",
           set(s.keys()) == set(SUPPORTED_LANGUAGES) and all(s.values()))

    s2 = _stub_summary(_sample_results())
    _check("T27 sample results → mentions both categories",
           "technical=" in s2["en"] and "content=" in s2["en"])


def test_synthesize_stub():
    print("\n== _synthesize_stub ==")
    insights, imps = _synthesize_stub(
        _sample_results(), "ko", max_improvements=10,
        fallback_reason="test_reason",
    )
    _check("T28 stub synthesized_by=stub-fallback",
           insights["synthesized_by"] == "stub-fallback")
    _check("T29 stub fallback_reason recorded",
           insights["fallback_reason"] == "test_reason")
    _check("T30 stub primary_language passed through",
           insights["primary_language"] == "ko")
    # 4 fail metrics → 4 improvements
    _check(f"T31 stub generates one improvement per fail (4 fails)",
           len(imps) == 4)
    _check("T32 stub priorities follow rank (high/medium/low/low)",
           imps[0].priority == "high"
           and imps[1].priority == "medium"
           and imps[2].priority == "low"
           and imps[3].priority == "low")
    _check("T33 stub max_improvements truncates",
           len(_synthesize_stub(
               _sample_results(), "en", max_improvements=2,
               fallback_reason="t",
           )[1]) == 2)
    # 모든 description 3언어 채워짐
    _check("T34 stub description multilingual (en/ko/es)",
           all(set(i.description.keys()) == set(SUPPORTED_LANGUAGES) for i in imps))
    # title_key deterministic
    _check("T35 stub title_key from metric key",
           imps[0].title_key.startswith("scoring.")
           and imps[0].title_key.endswith(".improvement_title"))


# ─── synthesize() 통합 (stub branches) ──────────────────────────────────

async def test_synthesize_no_api_key():
    print("\n== synthesize() no api_key → stub ==")
    original_settings = synth_mod.get_settings
    _patch_settings(None)
    try:
        insights, imps = await synthesize(_sample_results(), primary_language="en")
        _check("T36 no api_key → synthesized_by=stub-fallback",
               insights["synthesized_by"] == "stub-fallback"
               and insights["fallback_reason"] == "no_api_key")
        _check("T37 no api_key → improvements still generated (4 fails)",
               len(imps) == 4)
    finally:
        synth_mod.get_settings = original_settings


async def test_synthesize_empty_input():
    print("\n== synthesize() empty input → stub ==")
    insights, imps = await synthesize({}, primary_language="en")
    _check("T38 empty → synthesized_by=stub-fallback",
           insights["synthesized_by"] == "stub-fallback")
    _check("T39 empty → 0 improvements + category_count=0",
           len(imps) == 0 and insights["category_count"] == 0)


# ─── synthesize() 통합 (LLM mock happy / fallback) ───────────────────────

async def test_synthesize_happy_path():
    print("\n== synthesize() happy path (tool_use response) ==")
    original_anthropic = synth_mod.anthropic.AsyncAnthropic
    original_settings = synth_mod.get_settings
    _patch_settings("test-key", model="claude-sonnet-4-6")

    tool_input = {
        "summary": _multi(en="strong tech", ko="강한 기술", es="técnico fuerte"),
        "improvements": [
            _imp_dict(priority="high", category="technical", metric_key="ssl_enabled", impact=9),
            _imp_dict(priority="medium", category="content", metric_key="readability", impact=6),
            _imp_dict(priority="low", category="technical", metric_key="sitemap_ok", impact=3),
        ],
    }
    client = _make_anthropic_client(_make_tool_use_response(tool_input))
    _patch_anthropic(client)
    try:
        insights, imps = await synthesize(_sample_results(), primary_language="en")
        _check("T40 happy → synthesized_by = configured model",
               insights["synthesized_by"] == "claude-sonnet-4-6")
        _check("T41 happy → 3 improvements built",
               len(imps) == 3)
        _check("T42 happy → summary multilingual passed through",
               insights["summary"]["en"] == "strong tech"
               and insights["summary"]["ko"] == "강한 기술"
               and insights["summary"]["es"] == "técnico fuerte")
        _check("T43 happy → improvements_count = len(imps)",
               insights["improvements_count"] == 3)
        _check("T44 happy → high_priority_capped = false",
               insights["high_priority_capped"] is False)
        # priority 분포 그대로
        prios = [i.priority for i in imps]
        _check("T45 happy → priorities pass through (high/medium/low)",
               prios == ["high", "medium", "low"])
        # title_key deterministic
        _check("T46 happy → title_key from metric_key",
               imps[0].title_key == "scoring.technical.ssl_enabled.improvement_title")
        # tool_use 사용 검증
        call_kwargs = client.messages.create.call_args.kwargs
        _check("T47 happy → tools + tool_choice forced",
               call_kwargs["model"] == "claude-sonnet-4-6"
               and call_kwargs["tools"][0]["name"] == TOOL_NAME
               and call_kwargs["tool_choice"] == {"type": "tool", "name": TOOL_NAME})
    finally:
        _restore_anthropic(original_anthropic)
        synth_mod.get_settings = original_settings


async def test_synthesize_high_priority_capped():
    print("\n== synthesize() high priority cap ==")
    original_anthropic = synth_mod.anthropic.AsyncAnthropic
    original_settings = synth_mod.get_settings
    _patch_settings("test-key")

    tool_input = {
        "summary": _multi(),
        "improvements": [
            _imp_dict(priority="high", metric_key="ssl_enabled", impact=10),
            _imp_dict(priority="high", metric_key="sitemap_ok", impact=8),
            _imp_dict(priority="high", category="content", metric_key="readability", impact=7),
            _imp_dict(priority="high", category="content", metric_key="freshness_days", impact=4),  # demote
        ],
    }
    client = _make_anthropic_client(_make_tool_use_response(tool_input))
    _patch_anthropic(client)
    try:
        insights, imps = await synthesize(_sample_results(), primary_language="en")
        high_count = sum(1 for i in imps if i.priority == "high")
        _check(f"T48 4 highs → capped to {HIGH_PRIORITY_CAP}",
               high_count == HIGH_PRIORITY_CAP)
        _check("T49 high_priority_capped flag = True",
               insights["high_priority_capped"] is True)
        # impact 4 가 medium 으로 강등
        demoted = [i for i in imps if i.estimated_impact == 4]
        _check("T50 lowest-impact high demoted to medium",
               len(demoted) == 1 and demoted[0].priority == "medium")
    finally:
        _restore_anthropic(original_anthropic)
        synth_mod.get_settings = original_settings


async def test_synthesize_llm_exception():
    print("\n== synthesize() LLM exception → stub fallback ==")
    original_anthropic = synth_mod.anthropic.AsyncAnthropic
    original_settings = synth_mod.get_settings
    _patch_settings("test-key")

    client = MagicMock()
    client.messages.create = AsyncMock(side_effect=RuntimeError("rate limit"))
    _patch_anthropic(client)
    try:
        insights, imps = await synthesize(_sample_results(), primary_language="en")
        _check("T51 LLM exception → synthesized_by=stub-fallback",
               insights["synthesized_by"] == "stub-fallback")
        _check("T52 fallback_reason includes exception text",
               "rate limit" in insights.get("fallback_reason", ""))
        _check("T53 fallback still produces improvements (4 fails)",
               len(imps) == 4)
    finally:
        _restore_anthropic(original_anthropic)
        synth_mod.get_settings = original_settings


async def test_synthesize_missing_tool_use():
    print("\n== synthesize() missing tool_use block → stub ==")
    original_anthropic = synth_mod.anthropic.AsyncAnthropic
    original_settings = synth_mod.get_settings
    _patch_settings("test-key")

    text_block = MagicMock(); text_block.type = "text"
    response = MagicMock(content=[text_block])
    client = _make_anthropic_client(response)
    _patch_anthropic(client)
    try:
        insights, _ = await synthesize(_sample_results(), primary_language="en")
        _check("T54 no tool_use block → stub-fallback",
               insights["synthesized_by"] == "stub-fallback"
               and insights["fallback_reason"] == "missing_tool_use_block")
    finally:
        _restore_anthropic(original_anthropic)
        synth_mod.get_settings = original_settings


async def test_synthesize_invalid_summary():
    print("\n== synthesize() summary missing langs → stub ==")
    original_anthropic = synth_mod.anthropic.AsyncAnthropic
    original_settings = synth_mod.get_settings
    _patch_settings("test-key")

    # ko 누락
    tool_input = {
        "summary": {"en": "ok", "es": "ok"},
        "improvements": [],
    }
    client = _make_anthropic_client(_make_tool_use_response(tool_input))
    _patch_anthropic(client)
    try:
        insights, _ = await synthesize(_sample_results(), primary_language="en")
        _check("T55 missing language → fallback",
               insights["synthesized_by"] == "stub-fallback"
               and insights["fallback_reason"] == "invalid_summary_multilingual")
    finally:
        _restore_anthropic(original_anthropic)
        synth_mod.get_settings = original_settings


async def test_synthesize_invalid_improvements_skipped():
    print("\n== synthesize() invalid improvements skipped, valid kept ==")
    original_anthropic = synth_mod.anthropic.AsyncAnthropic
    original_settings = synth_mod.get_settings
    _patch_settings("test-key")

    tool_input = {
        "summary": _multi(),
        "improvements": [
            # 1 정상
            _imp_dict(category="technical", metric_key="ssl_enabled"),
            # 2 invalid category
            _imp_dict(category="bogus", metric_key="readability"),
            # 3 invalid related_metric_keys length
            {**_imp_dict(category="content", metric_key="readability"),
             "related_metric_keys": ["readability", "freshness_days"]},
            # 4 정상
            _imp_dict(category="content", metric_key="freshness_days", priority="low"),
            # 5 invalid impact > 10
            _imp_dict(category="technical", metric_key="sitemap_ok", impact=20),
        ],
    }
    client = _make_anthropic_client(_make_tool_use_response(tool_input))
    _patch_anthropic(client)
    try:
        _, imps = await synthesize(_sample_results(), primary_language="en")
        _check("T56 5 raw → 2 valid kept",
               len(imps) == 2)
        kept_keys = {i.related_metric_keys[0] for i in imps}
        _check("T57 valid items preserved (ssl_enabled + freshness_days)",
               kept_keys == {"ssl_enabled", "freshness_days"})
    finally:
        _restore_anthropic(original_anthropic)
        synth_mod.get_settings = original_settings


async def test_synthesize_max_improvements_truncates():
    print("\n== synthesize() max_improvements truncates ==")
    original_anthropic = synth_mod.anthropic.AsyncAnthropic
    original_settings = synth_mod.get_settings
    _patch_settings("test-key")

    # LLM 이 3개 반환 + max=2 → 2만 유지
    tool_input = {
        "summary": _multi(),
        "improvements": [
            _imp_dict(category="technical", metric_key="ssl_enabled"),
            _imp_dict(category="content", metric_key="readability"),
            _imp_dict(category="technical", metric_key="sitemap_ok"),
        ],
    }
    client = _make_anthropic_client(_make_tool_use_response(tool_input))
    _patch_anthropic(client)
    try:
        _, imps = await synthesize(_sample_results(), primary_language="en", max_improvements=2)
        _check("T58 max_improvements=2 → 2 kept",
               len(imps) == 2)
        # schema 의 maxItems 가 max_improvements 와 일치하는지 (call args 검증)
        call_kwargs = client.messages.create.call_args.kwargs
        schema = call_kwargs["tools"][0]["input_schema"]
        _check("T59 tool schema maxItems = max_improvements",
               schema["properties"]["improvements"]["maxItems"] == 2)
    finally:
        _restore_anthropic(original_anthropic)
        synth_mod.get_settings = original_settings


# ─── runner ─────────────────────────────────────────────────────────────

async def main() -> int:
    test_build_tool_input_schema()
    test_build_prompt()
    test_extract_tool_input()
    test_build_improvement()
    test_cap_high_priority()
    test_stub_summary()
    test_synthesize_stub()
    await test_synthesize_no_api_key()
    await test_synthesize_empty_input()
    await test_synthesize_happy_path()
    await test_synthesize_high_priority_capped()
    await test_synthesize_llm_exception()
    await test_synthesize_missing_tool_use()
    await test_synthesize_invalid_summary()
    await test_synthesize_invalid_improvements_skipped()
    await test_synthesize_max_improvements_truncates()

    print("\n" + "=" * 60)
    if FAILED:
        print(f"FAILED ({len(FAILED)}):")
        for label in FAILED:
            print(f"  - {label}")
        return 1
    print("All llm_synthesizer v2 tests PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
