"""Structured 카테고리 v2 단위 테스트 — 외부 의존 ❌ (httpx MockTransport).

실행:
    Set-Location backend; $env:PYTHONUTF8="1"; $env:PYTHONPATH="$PWD"
    .venv\\Scripts\\python.exe scripts\\test_structured_v2.py

5 메트릭 (json_ld_present / open_graph_complete / meta_description /
heading_hierarchy / twitter_card) × 케이스 + analyze() 통합 happy/fail.
"""
from __future__ import annotations

import asyncio
import sys
from typing import Callable

import httpx
from bs4 import BeautifulSoup

from app.scoring.schemas import AnalysisOptions
from app.scoring.structured import (
    META_DESC_MAX_LEN,
    META_DESC_MIN_LEN,
    REQUIRED_OG_TAGS,
    _check_heading_hierarchy,
    _check_json_ld,
    _check_meta_description,
    _check_open_graph,
    _check_twitter_card,
    analyze,
)


# ─── 픽스처 ─────────────────────────────────────────────────────────────

FULL_HTML = f"""<!doctype html>
<html>
<head>
  <title>Structured Demo</title>
  <meta name="description" content="{'A' * 100}">
  <meta property="og:title" content="Demo">
  <meta property="og:description" content="A demo site for structured data testing">
  <meta property="og:image" content="https://example.test/cover.png">
  <meta property="og:url" content="https://example.test/">
  <meta name="twitter:card" content="summary_large_image">
  <script type="application/ld+json">
    {{"@context": "https://schema.org", "@type": "Organization", "name": "Demo"}}
  </script>
</head>
<body>
  <h1>Demo</h1>
  <h2>Section 1</h2>
  <h3>Sub 1.1</h3>
  <h2>Section 2</h2>
</body>
</html>
"""

NO_STRUCTURED_HTML = """<!doctype html>
<html><head><title>Bare</title></head>
<body><p>nothing structured</p></body>
</html>
"""

OG_PARTIAL_HTML = """<!doctype html>
<html><head>
  <meta property="og:title" content="Only title">
  <meta property="og:url" content="https://example.test/">
</head><body></body></html>
"""

JSONLD_ARRAY_HTML = """<!doctype html>
<html><head>
  <script type="application/ld+json">
  [
    {"@type": "Article", "headline": "x"},
    {"@type": "Organization", "name": "y"}
  ]
  </script>
</head><body></body></html>
"""

JSONLD_INVALID_HTML = """<!doctype html>
<html><head>
  <script type="application/ld+json">{ this is not json }</script>
</head><body></body></html>
"""

META_DESC_TOO_SHORT = (
    "<!doctype html><html><head><meta name=\"description\" content=\"too short\">"
    "</head><body></body></html>"
)

META_DESC_TOO_LONG = (
    "<!doctype html><html><head><meta name=\"description\" content=\""
    + "A" * 250
    + "\"></head><body></body></html>"
)

HEADING_MULTI_H1 = """<!doctype html>
<html><body>
  <h1>One</h1><h1>Two</h1><h2>Sub</h2>
</body></html>
"""

HEADING_SKIP_LEVEL = """<!doctype html>
<html><body>
  <h1>One</h1><h3>Skipped h2</h3>
</body></html>
"""

HEADING_NONE = "<!doctype html><html><body><p>no headings</p></body></html>"


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


def _make_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(
        transport=transport, headers={"User-Agent": "test/1.0"},
        follow_redirects=True, timeout=httpx.Timeout(5.0),
    )


# ─── _check_json_ld ─────────────────────────────────────────────────────

def test_json_ld_dict() -> None:
    print("\n[T01] json_ld — dict @type → passed")
    m = _check_json_ld(_soup(FULL_HTML), None)
    assertion(m.passed is True, "passed=True")
    assertion(m.value == 1, "value=type count")
    assertion(m.evidence is not None and "Organization" in m.evidence, "evidence has type name")


def test_json_ld_array() -> None:
    print("\n[T02] json_ld — array of dicts → passed")
    m = _check_json_ld(_soup(JSONLD_ARRAY_HTML), None)
    assertion(m.passed is True, "passed=True")
    assertion(m.value == 2, "value=2 (array)")
    assertion(m.evidence is not None and "Article" in m.evidence and "Organization" in m.evidence, "both types in evidence")


def test_json_ld_absent() -> None:
    print("\n[T03] json_ld — no script → passed=False")
    m = _check_json_ld(_soup(NO_STRUCTURED_HTML), None)
    assertion(m.passed is False, "passed=False")
    assertion(m.value == 0, "value=0")


def test_json_ld_invalid() -> None:
    print("\n[T04] json_ld — invalid JSON → passed=False (no exception)")
    m = _check_json_ld(_soup(JSONLD_INVALID_HTML), None)
    assertion(m.passed is False, "passed=False")
    assertion(m.evidence is not None and "no application/ld+json" in m.evidence, "evidence indicates none")


def test_json_ld_no_soup() -> None:
    print("\n[T05] json_ld — soup=None → fetch error propagated")
    m = _check_json_ld(None, "HTTP 500")
    assertion(m.passed is False, "passed=False")
    assertion(m.evidence is not None and "HTTP 500" in m.evidence, "evidence carries fetch_error")


# ─── _check_open_graph ──────────────────────────────────────────────────

def test_og_complete() -> None:
    print("\n[T06] open_graph — all 4 tags present → passed")
    m = _check_open_graph(_soup(FULL_HTML), None)
    assertion(m.passed is True, "passed=True")
    assertion(m.value == 4, "value=4")
    assertion(m.threshold == 4.0, "threshold=4")


def test_og_partial() -> None:
    print("\n[T07] open_graph — only 2 tags → passed=False")
    m = _check_open_graph(_soup(OG_PARTIAL_HTML), None)
    assertion(m.passed is False, "passed=False")
    assertion(m.value == 2, "value=2 (found count)")
    assertion(m.evidence is not None and "missing" in m.evidence, "evidence lists missing")


def test_og_absent() -> None:
    print("\n[T08] open_graph — no og tags → passed=False")
    m = _check_open_graph(_soup(NO_STRUCTURED_HTML), None)
    assertion(m.passed is False, "passed=False")
    assertion(m.value == 0, "value=0")


def test_og_required_tags() -> None:
    print("\n[T09] open_graph — REQUIRED_OG_TAGS contains 4 tags")
    assertion(len(REQUIRED_OG_TAGS) == 4, "4 required og tags")
    assertion("og:title" in REQUIRED_OG_TAGS, "og:title required")


# ─── _check_meta_description ───────────────────────────────────────────

def test_meta_desc_in_range() -> None:
    print("\n[T10] meta_description — length in [50,200] → passed")
    m = _check_meta_description(_soup(FULL_HTML), None)
    assertion(m.passed is True, "passed=True")
    assertion(m.value == 100, "value=length=100")


def test_meta_desc_too_short() -> None:
    print("\n[T11] meta_description — under min → passed=False")
    m = _check_meta_description(_soup(META_DESC_TOO_SHORT), None)
    assertion(m.passed is False, "passed=False")
    assertion(m.value == len("too short"), "value=actual length")


def test_meta_desc_too_long() -> None:
    print("\n[T12] meta_description — over max → passed=False")
    m = _check_meta_description(_soup(META_DESC_TOO_LONG), None)
    assertion(m.passed is False, "passed=False")
    assertion(m.value == 250, "value=250")


def test_meta_desc_absent() -> None:
    print("\n[T13] meta_description — meta missing → passed=False")
    m = _check_meta_description(_soup(NO_STRUCTURED_HTML), None)
    assertion(m.passed is False, "passed=False")
    assertion(m.value == 0, "value=0")


def test_meta_desc_thresholds() -> None:
    print("\n[T14] meta_description — threshold consts are sensible")
    assertion(META_DESC_MIN_LEN < META_DESC_MAX_LEN, "min < max")
    assertion(META_DESC_MIN_LEN >= 50, "min >= 50 (SEO sane)")


# ─── _check_heading_hierarchy ──────────────────────────────────────────

def test_heading_ok() -> None:
    print("\n[T15] heading_hierarchy — h1×1 + h2 + h3 → passed")
    m = _check_heading_hierarchy(_soup(FULL_HTML), None)
    assertion(m.passed is True, "passed=True")
    assertion(m.value is not None and "h1=1" in str(m.value), "value carries counts")


def test_heading_multi_h1() -> None:
    print("\n[T16] heading_hierarchy — multiple h1 → passed=False")
    m = _check_heading_hierarchy(_soup(HEADING_MULTI_H1), None)
    assertion(m.passed is False, "passed=False")
    assertion(m.evidence is not None and "multiple h1" in m.evidence, "evidence flags multi-h1")


def test_heading_skip() -> None:
    print("\n[T17] heading_hierarchy — h3 without h2 → passed=False")
    m = _check_heading_hierarchy(_soup(HEADING_SKIP_LEVEL), None)
    assertion(m.passed is False, "passed=False")
    assertion(m.evidence is not None and "h3 without h2" in m.evidence, "evidence flags skip")


def test_heading_none() -> None:
    print("\n[T18] heading_hierarchy — no headings → passed=False")
    m = _check_heading_hierarchy(_soup(HEADING_NONE), None)
    assertion(m.passed is False, "passed=False")
    assertion(m.evidence is not None and "no headings" in m.evidence, "evidence=no headings")


# ─── _check_twitter_card ───────────────────────────────────────────────

def test_twitter_present() -> None:
    print("\n[T19] twitter_card — meta present → passed")
    m = _check_twitter_card(_soup(FULL_HTML), None)
    assertion(m.passed is True, "passed=True")
    assertion(m.value == "summary_large_image", "value=card type preserved")


def test_twitter_absent() -> None:
    print("\n[T20] twitter_card — meta missing → passed=False")
    m = _check_twitter_card(_soup(NO_STRUCTURED_HTML), None)
    assertion(m.passed is False, "passed=False")
    assertion(m.value is None, "value=None")


def test_twitter_no_soup() -> None:
    print("\n[T21] twitter_card — soup=None propagates")
    m = _check_twitter_card(None, "HTTP 404")
    assertion(m.passed is False, "passed=False")
    assertion(m.evidence is not None and "HTTP 404" in m.evidence, "evidence carries fetch_error")


# ─── analyze() 통합 ────────────────────────────────────────────────────

async def test_analyze_full_happy() -> None:
    print("\n[T22] analyze() — full happy → 5 metrics passed, score=100")

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=FULL_HTML, headers={"Content-Type": "text/html"})

    import app.scoring.structured as struct_mod

    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)

    def mock_async_client(*args, **kwargs):  # noqa: ANN001
        kwargs.pop("transport", None)
        return real_client(transport=transport, **kwargs)

    struct_mod.httpx.AsyncClient = mock_async_client  # type: ignore[assignment]
    try:
        result = await analyze("https://example.test/", AnalysisOptions())
    finally:
        struct_mod.httpx.AsyncClient = real_client  # type: ignore[assignment]

    assertion(len(result.metrics) == 5, "5 metrics returned")
    keys = {m.key for m in result.metrics}
    assertion(keys == {
        "json_ld_present", "open_graph_complete", "meta_description",
        "heading_hierarchy", "twitter_card",
    }, "metric keys = 5")
    assertion(all(m.passed for m in result.metrics), "all passed")
    assertion(result.score == 100.0, f"score=100.0 (got {result.score})")


async def test_analyze_total_failure() -> None:
    print("\n[T23] analyze() — connect error → all 5 metrics fail")

    def handler(_req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated outage")

    import app.scoring.structured as struct_mod

    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)

    def mock_async_client(*args, **kwargs):  # noqa: ANN001
        kwargs.pop("transport", None)
        return real_client(transport=transport, **kwargs)

    struct_mod.httpx.AsyncClient = mock_async_client  # type: ignore[assignment]
    try:
        result = await analyze("https://x.test/", AnalysisOptions())
    finally:
        struct_mod.httpx.AsyncClient = real_client  # type: ignore[assignment]

    assertion(len(result.metrics) == 5, "5 metrics returned")
    assertion(not any(m.passed for m in result.metrics), "no metrics passed")
    assertion(result.score == 0.0, f"score=0.0 (got {result.score})")
    fail_with_evidence = [
        m for m in result.metrics
        if m.evidence and "main page unavailable" in m.evidence
    ]
    assertion(len(fail_with_evidence) == 5, "all 5 metrics carry 'main page unavailable' evidence")


# ─── runner ─────────────────────────────────────────────────────────────

async def main() -> int:
    test_json_ld_dict()
    test_json_ld_array()
    test_json_ld_absent()
    test_json_ld_invalid()
    test_json_ld_no_soup()
    test_og_complete()
    test_og_partial()
    test_og_absent()
    test_og_required_tags()
    test_meta_desc_in_range()
    test_meta_desc_too_short()
    test_meta_desc_too_long()
    test_meta_desc_absent()
    test_meta_desc_thresholds()
    test_heading_ok()
    test_heading_multi_h1()
    test_heading_skip()
    test_heading_none()
    test_twitter_present()
    test_twitter_absent()
    test_twitter_no_soup()
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
