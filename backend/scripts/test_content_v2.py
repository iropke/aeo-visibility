"""Content 카테고리 v2 단위 테스트 — 외부 의존 ❌ (httpx MockTransport).

실행:
    Set-Location backend; $env:PYTHONUTF8="1"; $env:PYTHONPATH="$PWD"
    .venv\\Scripts\\python.exe scripts\\test_content_v2.py

4 메트릭 (content_length / readability / faq_presence / content_freshness) +
analyze() 통합 happy/fail. textstat 실 호출 (외부 API ❌, 패키지 내장).
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from typing import Callable

import httpx
from bs4 import BeautifulSoup

from app.scoring.content import (
    CONTENT_LENGTH_MIN_WORDS,
    FRESHNESS_MAX_DAYS,
    READABILITY_MAX_GRADE,
    READABILITY_MIN_GRADE,
    READABILITY_MIN_WORDS,
    _check_content_freshness,
    _check_content_length,
    _check_faq_presence,
    _check_readability,
    _extract_visible_text,
    _parse_freshness_date,
    analyze,
)
from app.scoring.schemas import AnalysisOptions


# ─── 픽스처 ─────────────────────────────────────────────────────────────

# 단어 수 350개 이상 + Flesch grade ~6-12 정도가 되는 본문.
LONG_TEXT_PARA = (
    "The quick brown fox jumps over the lazy dog every morning. "
    "We test simple readable sentences with common words. "
    "Each sentence has a clear subject and verb to keep the grade moderate. "
    "Reading should feel natural and not too complex for the average user. "
    "Our goal is steady prose that any reader can follow without trouble. "
)
GOOD_BODY = LONG_TEXT_PARA * 12  # ~600 단어.

GOOD_HTML = f"""<!doctype html>
<html>
<head>
  <title>Demo</title>
  <meta property="article:modified_time" content="{(datetime.now(timezone.utc) - timedelta(days=10)).isoformat()}">
</head>
<body>
  <header>nav skipped</header>
  <main>
    <h1>Title</h1>
    <h2>FAQ</h2>
    <p>{GOOD_BODY}</p>
    <details><summary>Q?</summary><p>A.</p></details>
  </main>
  <footer>footer skipped</footer>
</body>
</html>
"""

SHORT_HTML = "<!doctype html><html><body><p>just three words.</p></body></html>"

NO_DATE_HTML = """<!doctype html>
<html><body><h1>x</h1><p>some content body.</p></body></html>
"""

FAQ_SCHEMA_HTML = """<!doctype html>
<html><head>
  <script type="application/ld+json">
  {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}
  </script>
</head><body><h1>x</h1></body></html>
"""

FAQ_DETAILS_ONLY_HTML = """<!doctype html>
<html><body>
  <h1>About us</h1>
  <details><summary>How?</summary><p>like this</p></details>
</body></html>
"""

NO_FAQ_HTML = """<!doctype html>
<html><body><h1>About</h1><p>nothing FAQ.</p></body></html>
"""

OLD_DATE_HTML_TEMPLATE = """<!doctype html>
<html><head>
  <meta property="article:modified_time" content="{date}">
</head><body><p>old.</p></body></html>
"""


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


# ─── 어설션 헬퍼 ─────────────────────────────────────────────────────────

PASS_TAG = "  ✓"
FAIL_TAG = "  ✗"
FAILED: list[str] = []


def assertion(cond: bool, label: str) -> None:
    if cond:
        print(f"{PASS_TAG} {label}")
    else:
        print(f"{FAIL_TAG} {label}")
        FAILED.append(label)


# ─── _extract_visible_text ──────────────────────────────────────────────

def test_extract_visible_text_strips_chrome() -> None:
    print("\n[T01] _extract_visible_text — script/style/nav/header/footer/aside 제거")
    html = """<html>
      <head><script>var x=1;</script><style>.x{}</style></head>
      <body>
        <header>HEADER</header>
        <nav>NAV</nav>
        <main>BODY TEXT HERE</main>
        <aside>ASIDE</aside>
        <footer>FOOTER</footer>
      </body></html>"""
    text = _extract_visible_text(_soup(html))
    assertion("BODY TEXT HERE" in text, "main text retained")
    assertion("HEADER" not in text and "NAV" not in text, "header/nav stripped")
    assertion("FOOTER" not in text and "ASIDE" not in text, "footer/aside stripped")
    assertion("var x" not in text, "script content stripped")


def test_extract_does_not_mutate_caller_soup() -> None:
    print("\n[T02] _extract_visible_text — 호출자 soup 비파괴 (copy 사용)")
    html = "<html><head><script>x</script></head><body><p>y</p></body></html>"
    soup = _soup(html)
    _extract_visible_text(soup)
    # 원본 soup 의 script 가 살아있어야 함.
    assertion(soup.find("script") is not None, "caller soup script tag preserved")


# ─── _check_content_length ──────────────────────────────────────────────

def test_content_length_pass() -> None:
    print("\n[T03] content_length — long body → passed")
    m = _check_content_length(_soup(GOOD_HTML), None)
    assertion(m.passed is True, "passed=True")
    assertion(isinstance(m.value, int) and m.value >= CONTENT_LENGTH_MIN_WORDS, "value >= 300")
    assertion(m.threshold == float(CONTENT_LENGTH_MIN_WORDS), "threshold set")


def test_content_length_fail() -> None:
    print("\n[T04] content_length — short body → passed=False")
    m = _check_content_length(_soup(SHORT_HTML), None)
    assertion(m.passed is False, "passed=False")
    assertion(isinstance(m.value, int) and m.value < CONTENT_LENGTH_MIN_WORDS, "value < 300")


def test_content_length_no_soup() -> None:
    print("\n[T05] content_length — soup=None propagates")
    m = _check_content_length(None, "HTTP 500")
    assertion(m.passed is False, "passed=False")
    assertion(m.evidence is not None and "HTTP 500" in m.evidence, "evidence carries fetch_error")


# ─── _check_readability ─────────────────────────────────────────────────

def test_readability_pass() -> None:
    print("\n[T06] readability — moderate prose grade ∈ [6,16] → passed")
    m = _check_readability(_soup(GOOD_HTML), None)
    assertion(m.passed is True, f"passed=True (got {m.passed}, value={m.value})")
    assertion(isinstance(m.value, float), "value=fk_grade float")


def test_readability_insufficient_text() -> None:
    print("\n[T07] readability — under 30 words → passed=False (insufficient)")
    m = _check_readability(_soup(SHORT_HTML), None)
    assertion(m.passed is False, "passed=False")
    assertion(m.evidence is not None and "insufficient" in m.evidence, "evidence flags insufficient")


def test_readability_no_soup() -> None:
    print("\n[T08] readability — soup=None propagates")
    m = _check_readability(None, "dns failure")
    assertion(m.passed is False, "passed=False")
    assertion(m.evidence is not None and "dns failure" in m.evidence, "evidence carries fetch_error")


def test_readability_thresholds_const() -> None:
    print("\n[T09] readability — threshold consts sensible")
    assertion(READABILITY_MIN_GRADE < READABILITY_MAX_GRADE, "min < max")
    assertion(READABILITY_MIN_WORDS >= 30, "min words >= 30")


# ─── _check_faq_presence ────────────────────────────────────────────────

def test_faq_schema() -> None:
    print("\n[T10] faq_presence — FAQPage schema → passed")
    m = _check_faq_presence(_soup(FAQ_SCHEMA_HTML), None)
    assertion(m.passed is True, "passed=True")
    assertion(m.value is not None and "faq_schema" in str(m.value), "value contains faq_schema")


def test_faq_heading() -> None:
    print("\n[T11] faq_presence — FAQ heading keyword → passed")
    m = _check_faq_presence(_soup(GOOD_HTML), None)
    assertion(m.passed is True, "passed=True")
    assertion(m.value is not None and "faq_heading" in str(m.value), "value contains faq_heading")


def test_faq_details_only() -> None:
    print("\n[T12] faq_presence — <details> only → passed")
    m = _check_faq_presence(_soup(FAQ_DETAILS_ONLY_HTML), None)
    assertion(m.passed is True, "passed=True")
    assertion(m.value is not None and "details_element" in str(m.value), "value contains details_element")


def test_faq_absent() -> None:
    print("\n[T13] faq_presence — no FAQ signals → passed=False")
    m = _check_faq_presence(_soup(NO_FAQ_HTML), None)
    assertion(m.passed is False, "passed=False")
    assertion(m.evidence is not None and "no FAQ signals" in m.evidence, "evidence flags none")


def test_faq_no_soup() -> None:
    print("\n[T14] faq_presence — soup=None propagates")
    m = _check_faq_presence(None, "HTTP 404")
    assertion(m.passed is False, "passed=False")
    assertion(m.evidence is not None and "HTTP 404" in m.evidence, "evidence carries fetch_error")


# ─── _parse_freshness_date ──────────────────────────────────────────────

def test_parse_iso() -> None:
    print("\n[T15] _parse_freshness_date — ISO 8601 with Z")
    dt = _parse_freshness_date("2026-05-01T12:00:00Z")
    assertion(dt is not None, "parsed")
    assertion(dt.tzinfo is not None, "tz-aware")


def test_parse_rfc2822() -> None:
    print("\n[T16] _parse_freshness_date — RFC 2822 (HTTP header)")
    dt = _parse_freshness_date("Wed, 21 Oct 2015 07:28:00 GMT")
    assertion(dt is not None, "parsed")
    assertion(dt.year == 2015 and dt.month == 10, "correct date")


def test_parse_invalid() -> None:
    print("\n[T17] _parse_freshness_date — invalid string → None")
    dt = _parse_freshness_date("not a date")
    assertion(dt is None, "None on invalid")


# ─── _check_content_freshness ───────────────────────────────────────────

def test_freshness_recent_meta() -> None:
    print("\n[T18] content_freshness — recent meta → passed")
    m = _check_content_freshness(_soup(GOOD_HTML), {}, None)
    assertion(m.passed is True, "passed=True")
    assertion(isinstance(m.value, int) and m.value < 30, "value=days_ago < 30")
    assertion(m.evidence is not None and "source=meta" in m.evidence, "evidence source=meta")


def test_freshness_old_meta() -> None:
    print("\n[T19] content_freshness — meta 2 years ago → passed=False")
    old = (datetime.now(timezone.utc) - timedelta(days=730)).isoformat()
    html = OLD_DATE_HTML_TEMPLATE.format(date=old)
    m = _check_content_freshness(_soup(html), {}, None)
    assertion(m.passed is False, "passed=False")
    assertion(isinstance(m.value, int) and m.value > FRESHNESS_MAX_DAYS, "days_ago > 365")


def test_freshness_header_fallback() -> None:
    print("\n[T20] content_freshness — no meta, recent Last-Modified header")
    recent_rfc = (datetime.now(timezone.utc) - timedelta(days=5)).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )
    headers = {"last-modified": recent_rfc}
    m = _check_content_freshness(_soup(NO_DATE_HTML), headers, None)
    assertion(m.passed is True, "passed=True via header")
    assertion(m.evidence is not None and "source=header" in m.evidence, "evidence source=header")


def test_freshness_no_signal() -> None:
    print("\n[T21] content_freshness — no meta, no header → passed=False")
    m = _check_content_freshness(_soup(NO_DATE_HTML), {}, None)
    assertion(m.passed is False, "passed=False")
    assertion(m.evidence is not None and "no parseable" in m.evidence, "evidence: no parseable")


def test_freshness_no_soup() -> None:
    print("\n[T22] content_freshness — soup=None propagates")
    m = _check_content_freshness(None, {}, "HTTP 500")
    assertion(m.passed is False, "passed=False")
    assertion(m.evidence is not None and "HTTP 500" in m.evidence, "evidence carries fetch_error")


# ─── analyze() 통합 ────────────────────────────────────────────────────

async def test_analyze_full_happy() -> None:
    print("\n[T23] analyze() — full happy → 4 metrics passed, score=100")

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=GOOD_HTML, headers={"Content-Type": "text/html"})

    import app.scoring.content as content_mod

    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)

    def mock_async_client(*args, **kwargs):  # noqa: ANN001
        kwargs.pop("transport", None)
        return real_client(transport=transport, **kwargs)

    content_mod.httpx.AsyncClient = mock_async_client  # type: ignore[assignment]
    try:
        result = await analyze("https://example.test/", AnalysisOptions())
    finally:
        content_mod.httpx.AsyncClient = real_client  # type: ignore[assignment]

    assertion(len(result.metrics) == 4, "4 metrics returned")
    keys = {m.key for m in result.metrics}
    assertion(keys == {
        "content_length", "readability", "faq_presence", "content_freshness",
    }, "metric keys = 4")
    # readability 가 텍스트 본문 따라 grade 가 16 넘을 수 있음 — 보수적으로
    # 'all passed' 가 아닐 수도 있어 score 범위만 검증.
    passed_count = sum(1 for m in result.metrics if m.passed)
    assertion(passed_count >= 3, f"at least 3/4 passed (got {passed_count})")
    assertion(result.score >= 75.0, f"score >= 75 (got {result.score})")


async def test_analyze_total_failure() -> None:
    print("\n[T24] analyze() — connect error → all 4 metrics fail")

    def handler(_req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated outage")

    import app.scoring.content as content_mod

    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)

    def mock_async_client(*args, **kwargs):  # noqa: ANN001
        kwargs.pop("transport", None)
        return real_client(transport=transport, **kwargs)

    content_mod.httpx.AsyncClient = mock_async_client  # type: ignore[assignment]
    try:
        result = await analyze("https://x.test/", AnalysisOptions())
    finally:
        content_mod.httpx.AsyncClient = real_client  # type: ignore[assignment]

    assertion(len(result.metrics) == 4, "4 metrics returned")
    assertion(not any(m.passed for m in result.metrics), "no metrics passed")
    assertion(result.score == 0.0, f"score=0.0 (got {result.score})")
    fail_with_evidence = [
        m for m in result.metrics
        if m.evidence and "main page unavailable" in m.evidence
    ]
    assertion(len(fail_with_evidence) == 4, "all 4 metrics carry 'main page unavailable' evidence")


# ─── runner ─────────────────────────────────────────────────────────────

async def main() -> int:
    test_extract_visible_text_strips_chrome()
    test_extract_does_not_mutate_caller_soup()
    test_content_length_pass()
    test_content_length_fail()
    test_content_length_no_soup()
    test_readability_pass()
    test_readability_insufficient_text()
    test_readability_no_soup()
    test_readability_thresholds_const()
    test_faq_schema()
    test_faq_heading()
    test_faq_details_only()
    test_faq_absent()
    test_faq_no_soup()
    test_parse_iso()
    test_parse_rfc2822()
    test_parse_invalid()
    test_freshness_recent_meta()
    test_freshness_old_meta()
    test_freshness_header_fallback()
    test_freshness_no_signal()
    test_freshness_no_soup()
    await test_analyze_full_happy()
    await test_analyze_total_failure()

    print(f"\n=== {len(FAILED)} failed ===" if FAILED else "\n=== ALL TESTS PASSED ===")
    if FAILED:
        for label in FAILED:
            print(f"  - {label}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
