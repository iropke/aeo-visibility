"""Visibility 카테고리 v2 단위 테스트 — 외부 의존 ❌ (anthropic + httpx mock).

실행:
    Set-Location backend; $env:PYTHONUTF8="1"; $env:PYTHONPATH="$PWD"
    .venv\\Scripts\\python.exe scripts\\test_visibility_v2.py

3 메트릭 (llm_brand_mention / llm_domain_mention / queries_tested) +
analyze() 통합 (stub 분기 + LLM mock 분기). v1 _generate_queries 시퀀스 +
brand/domain 매치 로직 검증.

mock 패턴:
- anthropic.AsyncAnthropic → MagicMock(return_value=mock_client) 로 교체.
- mock_client.messages.create → AsyncMock 으로 응답 객체 시퀀스 반환.
- httpx.AsyncClient → mock_factory (transport 만 교체).
- get_settings → monkey-patch 로 claude_api_key 시뮬레이션.
"""
from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx

from app.scoring import visibility as vis_mod
from app.scoring.schemas import AnalysisOptions
from app.scoring.visibility import (
    BRAND_MIN_LENGTH,
    QUERIES_FALLBACK_COUNT,
    QUERIES_TARGET_COUNT,
    _brand_token,
    _check_query_visibility,
    _domain_from_url,
    _extract_site_topic,
    _fallback_queries,
    _format_query_evidence,
    _generate_queries,
    analyze,
)


# ─── 픽스처 ─────────────────────────────────────────────────────────────

GOOD_HTML = """<!doctype html><html>
<head>
  <title>Example Co</title>
  <meta name="description" content="We sell widgets and gadgets.">
</head>
<body>
  <h1>Welcome to Example</h1>
  <p>Body content here.</p>
</body></html>
"""


def _make_message(text: str) -> MagicMock:
    """anthropic Message 응답 객체 mock — content[0].text 접근 가능."""
    return MagicMock(content=[MagicMock(text=text)])


def _make_anthropic_client(create_side_effect) -> MagicMock:
    """AsyncAnthropic 인스턴스 mock — messages.create 가 mock."""
    client = MagicMock()
    if isinstance(create_side_effect, list):
        client.messages.create = AsyncMock(side_effect=create_side_effect)
    else:
        client.messages.create = AsyncMock(return_value=create_side_effect)
    return client


def _patch_anthropic(client: MagicMock):
    """vis_mod.anthropic.AsyncAnthropic 을 client 반환 factory 로 교체."""
    vis_mod.anthropic.AsyncAnthropic = MagicMock(return_value=client)


def _restore_anthropic(original):
    vis_mod.anthropic.AsyncAnthropic = original


def _patch_settings(api_key: str | None):
    """get_settings() 가 .claude_api_key 만 가진 객체 반환하도록 monkey-patch."""
    fake = SimpleNamespace(claude_api_key=api_key)
    vis_mod.get_settings = lambda: fake


def _make_http_factory(html: str = GOOD_HTML, status: int = 200):
    """httpx.AsyncClient mock factory — transport 만 교체, 나머지 위임."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=status,
            text=html if status < 400 else "",
            headers={"Content-Type": "text/html; charset=utf-8"},
        )
    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)
    return factory


def _make_http_factory_error(error: Exception):
    """fetch 실패 시뮬레이션 — 항상 예외 raise."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise error
    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)
    return factory


FAILED: list[str] = []


def _check(label: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    suffix = f" — {detail}" if detail and not cond else ""
    print(f"  [{status}] {label}{suffix}")
    if not cond:
        FAILED.append(label)


# ─── 헬퍼 단위 테스트 ─────────────────────────────────────────────────

def test_domain_from_url():
    print("\n== _domain_from_url ==")
    _check("T01 https://example.com → example.com",
           _domain_from_url("https://example.com") == "example.com")
    _check("T02 https://www.example.com/path → example.com",
           _domain_from_url("https://www.example.com/path") == "example.com")


def test_brand_token():
    print("\n== _brand_token ==")
    _check("T03 example.com → 'example'",
           _brand_token("example.com") == "example")
    _check("T04 short.io → 'short'",
           _brand_token("short.io") == "short")


def test_extract_site_topic():
    print("\n== _extract_site_topic ==")
    from bs4 import BeautifulSoup
    from app.scoring._common import MainPage

    soup = BeautifulSoup(GOOD_HTML, "lxml")
    main_page = MainPage(
        status_code=200, elapsed_ms=1.0, content_size=len(GOOD_HTML),
        final_url="https://example.com", soup=soup, error=None, headers={},
    )
    topic = _extract_site_topic(main_page, "example.com")
    _check("T05 full topic includes title/desc/h1",
           "Example Co" in topic and "widgets" in topic and "Welcome to Example" in topic,
           detail=topic[:80])

    no_soup_page = MainPage(
        status_code=0, elapsed_ms=0.0, content_size=0,
        final_url="https://x.com", soup=None, error="net", headers={},
    )
    _check("T06 no soup → fallback domain",
           _extract_site_topic(no_soup_page, "fallback.com") == "fallback.com")

    bare_html = "<html><body><p>x</p></body></html>"
    bare_soup = BeautifulSoup(bare_html, "lxml")
    bare_page = MainPage(
        status_code=200, elapsed_ms=1.0, content_size=len(bare_html),
        final_url="https://x.com", soup=bare_soup, error=None, headers={},
    )
    _check("T07 no title/desc/h1 → fallback domain",
           _extract_site_topic(bare_page, "x.com") == "x.com")


def test_fallback_queries():
    print("\n== _fallback_queries ==")
    qs = _fallback_queries("example.com")
    _check("T08 fallback returns N queries with domain",
           len(qs) == QUERIES_FALLBACK_COUNT and all("example.com" in q for q in qs))


def test_format_query_evidence():
    print("\n== _format_query_evidence ==")
    results = [
        {"query": "q1", "brand_match": True, "domain_match": False},
        {"query": "q2", "brand_match": True, "domain_match": True},
        {"query": "q3", "brand_match": False, "domain_match": False},
    ]
    e = _format_query_evidence(results, "brand_match")
    _check("T09 evidence includes matches=2/3",
           "matches=2/3" in e, detail=e)
    _check("T10 evidence includes per-query markers",
           "q=q1|m=1" in e and "q=q3|m=0" in e, detail=e)
    _check("T11 empty results → matches=0/0",
           "matches=0/0" in _format_query_evidence([], "brand_match"))


# ─── _generate_queries (LLM mock) ────────────────────────────────────

async def test_generate_queries():
    print("\n== _generate_queries ==")
    original_anthropic = vis_mod.anthropic.AsyncAnthropic

    # T12: 정상 5 line 응답.
    text = "query one\nquery two\nquery three\nquery four\nquery five"
    client = _make_anthropic_client(_make_message(text))
    qs, src = await _generate_queries(client, "topic", "example.com")
    _check("T12 LLM 5 lines → 5 queries source=llm",
           len(qs) == 5 and src == "llm" and qs[0] == "query one")

    # T13: 빈 응답 → fallback.
    client = _make_anthropic_client(_make_message(""))
    qs, src = await _generate_queries(client, "topic", "example.com")
    _check("T13 empty LLM response → fallback",
           len(qs) == QUERIES_FALLBACK_COUNT and src == "fallback")

    # T14: LLM 예외 → fallback.
    client = MagicMock()
    client.messages.create = AsyncMock(side_effect=RuntimeError("rate limit"))
    qs, src = await _generate_queries(client, "topic", "example.com")
    _check("T14 LLM exception → fallback",
           len(qs) == QUERIES_FALLBACK_COUNT and src == "fallback")

    # T15: 7 line → 처음 5만.
    text = "\n".join(f"q{i}" for i in range(1, 8))
    client = _make_anthropic_client(_make_message(text))
    qs, src = await _generate_queries(client, "topic", "example.com")
    _check("T15 7 lines → truncate to 5",
           len(qs) == 5 and qs[-1] == "q5" and src == "llm")

    _restore_anthropic(original_anthropic)


# ─── _check_query_visibility (LLM mock) ──────────────────────────────

async def test_check_query_visibility():
    print("\n== _check_query_visibility ==")
    # T16: domain 매치.
    client = _make_anthropic_client(
        _make_message("Visit https://example.com for widgets.")
    )
    r = await _check_query_visibility(client, "best widgets?", "example.com", "example")
    _check("T16 domain match",
           r["domain_match"] is True and r["brand_match"] is True)

    # T17: brand only (도메인 ❌, brand 만).
    client = _make_anthropic_client(
        _make_message("Example is a great company in widgets.")
    )
    r = await _check_query_visibility(client, "q?", "example.com", "example")
    _check("T17 brand match only",
           r["domain_match"] is False and r["brand_match"] is True)

    # T18: 둘 다 ❌.
    client = _make_anthropic_client(
        _make_message("Try Acme Corporation for the best service.")
    )
    r = await _check_query_visibility(client, "q?", "example.com", "example")
    _check("T18 no match",
           r["domain_match"] is False and r["brand_match"] is False)

    # T19: brand 너무 짧음 → brand_match=False.
    short_brand = "ab"  # < BRAND_MIN_LENGTH
    client = _make_anthropic_client(_make_message("ab is a substring everywhere"))
    r = await _check_query_visibility(client, "q?", "ab.com", short_brand)
    _check(f"T19 brand len < {BRAND_MIN_LENGTH} → no brand match",
           r["brand_match"] is False)

    # T20: 예외 → False + error 키.
    client = MagicMock()
    client.messages.create = AsyncMock(side_effect=RuntimeError("api down"))
    r = await _check_query_visibility(client, "q?", "example.com", "example")
    _check("T20 exception → both False + error key",
           r["domain_match"] is False and r["brand_match"] is False
           and "error" in r)


# ─── analyze() 통합 (stub 분기) ───────────────────────────────────────

async def test_analyze_stub_branches():
    print("\n== analyze() stub branches ==")
    # T21: enable_llm_visibility=False (기본).
    opts = AnalysisOptions()
    result = await analyze("https://example.com", opts)
    _check("T21 disabled → score=0, 3 metrics stub",
           result.score == 0 and len(result.metrics) == 3
           and all("disabled" in (m.evidence or "") for m in result.metrics))

    # T22: visibility_engines 에 claude 없음.
    opts = AnalysisOptions(
        enable_llm_visibility=True,
        visibility_engines=["gpt"],
    )
    result = await analyze("https://example.com", opts)
    _check("T22 no claude in engines → all stub",
           result.score == 0
           and all("no supported engine" in (m.evidence or "") for m in result.metrics))

    # T23: api_key=None.
    original_settings = vis_mod.get_settings
    _patch_settings(None)
    try:
        opts = AnalysisOptions(enable_llm_visibility=True)
        result = await analyze("https://example.com", opts)
        _check("T23 no api_key → all stub",
               result.score == 0
               and all("api_key" in (m.evidence or "") for m in result.metrics))
    finally:
        vis_mod.get_settings = original_settings


# ─── analyze() 통합 (LLM mock happy/fail) ────────────────────────────

async def test_analyze_full_happy():
    print("\n== analyze() full happy ==")
    original_anthropic = vis_mod.anthropic.AsyncAnthropic
    original_httpx = httpx.AsyncClient
    original_settings = vis_mod.get_settings
    _patch_settings("test-key")
    httpx.AsyncClient = _make_http_factory(GOOD_HTML)

    # query gen 응답 1 + visibility check 응답 5 (모두 매치).
    responses = [
        _make_message("q1\nq2\nq3\nq4\nq5"),
        *[_make_message("Check out https://example.com — Example is great.") for _ in range(5)],
    ]
    client = _make_anthropic_client(responses)
    _patch_anthropic(client)
    try:
        opts = AnalysisOptions(enable_llm_visibility=True)
        result = await analyze("https://example.com", opts)
        _check("T24 full happy → all 3 metrics passed",
               all(m.passed for m in result.metrics),
               detail=f"score={result.score}, evidences={[m.evidence[:40] for m in result.metrics]}")
        _check("T25 full happy → score 100",
               abs(result.score - 100.0) < 0.01,
               detail=f"score={result.score}")
        # 6 호출 시퀀스 (1 query gen + 5 checks)
        _check("T26 6 LLM calls (1 gen + 5 check)",
               client.messages.create.call_count == 6,
               detail=f"calls={client.messages.create.call_count}")
    finally:
        _restore_anthropic(original_anthropic)
        httpx.AsyncClient = original_httpx
        vis_mod.get_settings = original_settings


async def test_analyze_partial_match():
    print("\n== analyze() partial match (brand fail / domain fail / queries pass) ==")
    original_anthropic = vis_mod.anthropic.AsyncAnthropic
    original_httpx = httpx.AsyncClient
    original_settings = vis_mod.get_settings
    _patch_settings("test-key")
    httpx.AsyncClient = _make_http_factory(GOOD_HTML)

    # 5 query gen + 5 visibility check 모두 매치 ❌.
    responses = [
        _make_message("q1\nq2\nq3\nq4\nq5"),
        *[_make_message("Try Acme Corp for service.") for _ in range(5)],
    ]
    client = _make_anthropic_client(responses)
    _patch_anthropic(client)
    try:
        opts = AnalysisOptions(enable_llm_visibility=True)
        result = await analyze("https://example.com", opts)
        # weights: brand 0.50 / domain 0.30 / queries_tested 0.20 → only queries pass = 20.0
        _check("T27 partial → score = queries_tested weight only",
               abs(result.score - 20.0) < 0.01,
               detail=f"score={result.score}")
        keyed = {m.key: m for m in result.metrics}
        _check("T28 brand metric failed",
               keyed["llm_brand_mention"].passed is False)
        _check("T29 domain metric failed",
               keyed["llm_domain_mention"].passed is False)
        _check("T30 queries_tested metric passed (5 == target)",
               keyed["queries_tested"].passed is True)
    finally:
        _restore_anthropic(original_anthropic)
        httpx.AsyncClient = original_httpx
        vis_mod.get_settings = original_settings


async def test_analyze_user_queries():
    print("\n== analyze() user_queries ==")
    original_anthropic = vis_mod.anthropic.AsyncAnthropic
    original_httpx = httpx.AsyncClient
    original_settings = vis_mod.get_settings
    _patch_settings("test-key")
    httpx.AsyncClient = _make_http_factory(GOOD_HTML)

    # user 입력 6개 → 5개로 truncate. visibility check 5번만 호출.
    responses = [_make_message("Example.com is the best.") for _ in range(5)]
    client = _make_anthropic_client(responses)
    _patch_anthropic(client)
    try:
        opts = AnalysisOptions(
            enable_llm_visibility=True,
            visibility_user_queries=["q1", "q2", "q3", "q4", "q5", "q6"],
        )
        result = await analyze("https://example.com", opts)
        # 6 가 아니라 5 호출 (query gen ❌, user queries 5개 truncate).
        _check("T31 user queries skip query gen (5 calls only)",
               client.messages.create.call_count == 5,
               detail=f"calls={client.messages.create.call_count}")
        # source=user 가 evidence 에 들어가는지.
        _check("T32 evidence source=user",
               all("source=user" in (m.evidence or "") for m in result.metrics))
    finally:
        _restore_anthropic(original_anthropic)
        httpx.AsyncClient = original_httpx
        vis_mod.get_settings = original_settings


async def test_analyze_fallback_queries():
    print("\n== analyze() fallback queries (query gen fails) ==")
    original_anthropic = vis_mod.anthropic.AsyncAnthropic
    original_httpx = httpx.AsyncClient
    original_settings = vis_mod.get_settings
    _patch_settings("test-key")
    httpx.AsyncClient = _make_http_factory(GOOD_HTML)

    # query gen 실패 → fallback 3 queries → visibility check 3번.
    client = MagicMock()
    client.messages.create = AsyncMock(side_effect=[
        RuntimeError("rate limit"),  # query gen 실패
        *[_make_message("not matched") for _ in range(QUERIES_FALLBACK_COUNT)],
    ])
    _patch_anthropic(client)
    try:
        opts = AnalysisOptions(enable_llm_visibility=True)
        result = await analyze("https://example.com", opts)
        keyed = {m.key: m for m in result.metrics}
        # fallback 3 < target 5 → queries_tested fail.
        _check("T33 fallback queries → queries_tested fails (3 < 5)",
               keyed["queries_tested"].passed is False
               and keyed["queries_tested"].value == QUERIES_FALLBACK_COUNT)
        _check("T34 evidence source=fallback",
               "source=fallback" in (keyed["queries_tested"].evidence or ""))
    finally:
        _restore_anthropic(original_anthropic)
        httpx.AsyncClient = original_httpx
        vis_mod.get_settings = original_settings


async def test_analyze_fetch_fail():
    print("\n== analyze() main page fetch fail (LLM still runs) ==")
    original_anthropic = vis_mod.anthropic.AsyncAnthropic
    original_httpx = httpx.AsyncClient
    original_settings = vis_mod.get_settings
    _patch_settings("test-key")
    httpx.AsyncClient = _make_http_factory_error(httpx.ConnectError("dns fail"))

    # site_topic = domain (fallback). query gen 정상 + 5 check 매치.
    responses = [
        _make_message("q1\nq2\nq3\nq4\nq5"),
        *[_make_message("example.com is awesome") for _ in range(5)],
    ]
    client = _make_anthropic_client(responses)
    _patch_anthropic(client)
    try:
        opts = AnalysisOptions(enable_llm_visibility=True)
        result = await analyze("https://example.com", opts)
        _check("T35 fetch fail → LLM 6 calls still happen",
               client.messages.create.call_count == 6)
        _check("T36 fetch fail → metrics computed (not stub)",
               all(m.passed for m in result.metrics))
    finally:
        _restore_anthropic(original_anthropic)
        httpx.AsyncClient = original_httpx
        vis_mod.get_settings = original_settings


async def test_analyze_unsupported_engines_warning():
    print("\n== analyze() unsupported engines + claude → claude runs ==")
    original_anthropic = vis_mod.anthropic.AsyncAnthropic
    original_httpx = httpx.AsyncClient
    original_settings = vis_mod.get_settings
    _patch_settings("test-key")
    httpx.AsyncClient = _make_http_factory(GOOD_HTML)

    responses = [
        _make_message("q1\nq2\nq3\nq4\nq5"),
        *[_make_message("example") for _ in range(5)],
    ]
    client = _make_anthropic_client(responses)
    _patch_anthropic(client)
    try:
        opts = AnalysisOptions(
            enable_llm_visibility=True,
            visibility_engines=["claude", "gpt", "gemini"],
        )
        result = await analyze("https://example.com", opts)
        _check("T37 mixed engines (claude+others) → claude runs (6 calls)",
               client.messages.create.call_count == 6)
        _check("T38 metrics not stubbed (claude ran)",
               not any("disabled" in (m.evidence or "") for m in result.metrics))
    finally:
        _restore_anthropic(original_anthropic)
        httpx.AsyncClient = original_httpx
        vis_mod.get_settings = original_settings


# ─── runner ────────────────────────────────────────────────────────────

async def main():
    test_domain_from_url()
    test_brand_token()
    test_extract_site_topic()
    test_fallback_queries()
    test_format_query_evidence()
    await test_generate_queries()
    await test_check_query_visibility()
    await test_analyze_stub_branches()
    await test_analyze_full_happy()
    await test_analyze_partial_match()
    await test_analyze_user_queries()
    await test_analyze_fallback_queries()
    await test_analyze_fetch_fail()
    await test_analyze_unsupported_engines_warning()

    print("\n" + "=" * 60)
    if FAILED:
        print(f"FAILED: {len(FAILED)} cases")
        for label in FAILED:
            print(f"  - {label}")
        sys.exit(1)
    else:
        print(f"All cases PASS — {QUERIES_TARGET_COUNT}-query Claude visibility scoring verified.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
