"""Technical 카테고리 v2 단위 테스트 — httpx MockTransport 기반 (외부 의존 ❌).

실행: 백엔드 디렉토리에서
    Set-Location backend; $env:PYTHONUTF8="1"; $env:PYTHONPATH="$PWD"
    .venv\\Scripts\\python.exe scripts\\test_technical_v2.py

각 헬퍼 함수의 happy/fail 케이스 + analyze() 통합 happy/fail. 외부 사이트
호출 없음 — 모든 응답은 ``MockTransport`` 핸들러가 결정.

회귀 가치: 메트릭 키 6종 (ssl_enabled / robots_txt / sitemap_xml / canonical_tag
/ mobile_viewport / page_speed) 의 binary passed 변환 + evidence 보존.
"""
from __future__ import annotations

import asyncio
import sys
from typing import Callable

import httpx
from bs4 import BeautifulSoup

from app.scoring._common import MainPage, fetch_main_page
from app.scoring.schemas import AnalysisOptions
from app.scoring.technical import (
    PAGE_SPEED_THRESHOLD_MS,
    _check_canonical,
    _check_mobile_viewport,
    _check_page_speed,
    _check_robots_txt,
    _check_sitemap,
    _check_ssl,
    _domain_from_url,
    analyze,
)


# ─── 픽스처 ──────────────────────────────────────────────────────────────

GOOD_HTML = """<!doctype html>
<html>
<head>
  <link rel="canonical" href="https://example.test/">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sample</title>
</head>
<body><h1>Hello</h1></body>
</html>
"""

NO_CANONICAL_NO_VIEWPORT_HTML = """<!doctype html>
<html><head><title>Plain</title></head><body><p>Plain</p></body></html>
"""

VIEWPORT_NO_WIDTH_HTML = """<!doctype html>
<html><head><meta name="viewport" content="initial-scale=1"></head>
<body></body></html>
"""

ROBOTS_OK = "User-agent: *\nAllow: /\nSitemap: https://example.test/sitemap.xml\n"
ROBOTS_DISALLOW_ALL = "User-agent: *\nDisallow: /\n"
ROBOTS_EMPTY = ""

SITEMAP_OK = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    '<url><loc>https://example.test/</loc></url></urlset>'
)


def _make_client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.AsyncClient:
    """MockTransport + AsyncClient 헬퍼 — follow_redirects + UA 동일하게."""
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(
        transport=transport,
        headers={"User-Agent": "test-agent/1.0"},
        follow_redirects=True,
        timeout=httpx.Timeout(5.0),
    )


# ─── 어설션 헬퍼 ──────────────────────────────────────────────────────────

PASS = "  ✓"
FAIL_TAG = "  ✗"
FAILED: list[str] = []


def assertion(cond: bool, label: str) -> None:
    if cond:
        print(f"{PASS} {label}")
    else:
        print(f"{FAIL_TAG} {label}")
        FAILED.append(label)


# ─── _domain_from_url ────────────────────────────────────────────────────

def test_domain_extraction() -> None:
    print("\n[T01] _domain_from_url")
    assertion(_domain_from_url("https://example.test/") == "example.test", "scheme + path")
    assertion(_domain_from_url("https://example.test") == "example.test", "scheme only")
    assertion(_domain_from_url("example.test/x") == "example.test", "bare domain + path")
    assertion(_domain_from_url("example.test") == "example.test", "bare domain")


# ─── _fetch_main_page ────────────────────────────────────────────────────

async def test_fetch_main_page_200() -> None:
    print("\n[T02] _fetch_main_page — 200 OK")

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=GOOD_HTML, headers={"Content-Type": "text/html"})

    async with _make_client(handler) as client:
        page = await fetch_main_page(client, "https://example.test/")

    assertion(page.status_code == 200, "status_code=200")
    assertion(page.error is None, "no error")
    assertion(page.soup is not None, "soup parsed")
    assertion(page.final_url.startswith("https://example.test"), "final_url is https")


async def test_fetch_main_page_404() -> None:
    print("\n[T03] _fetch_main_page — 404")

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    async with _make_client(handler) as client:
        page = await fetch_main_page(client, "https://example.test/")

    assertion(page.status_code == 404, "status_code=404")
    assertion(page.error == "HTTP 404", "error=HTTP 404")
    assertion(page.soup is None, "soup is None for 4xx")


async def test_fetch_main_page_connection_error() -> None:
    print("\n[T04] _fetch_main_page — connection error")

    def handler(_req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("dns failure")

    async with _make_client(handler) as client:
        page = await fetch_main_page(client, "https://nonexistent.test/")

    assertion(page.status_code == 0, "status_code=0 on connect error")
    assertion(page.error is not None and "dns failure" in page.error, "error captured")
    assertion(page.soup is None, "soup is None")


# ─── _check_ssl ──────────────────────────────────────────────────────────

def test_check_ssl_https() -> None:
    print("\n[T05] _check_ssl — https final_url passes")
    page = MainPage(200, 100.0, 1024, "https://example.test/", None, None, {})
    m = _check_ssl(page)
    assertion(m.passed is True, "passed=True")
    assertion(m.value is True, "value=True")
    assertion(m.key == "ssl_enabled", "key=ssl_enabled")


def test_check_ssl_http() -> None:
    print("\n[T06] _check_ssl — http final_url fails")
    page = MainPage(200, 100.0, 1024, "http://example.test/", None, None, {})
    m = _check_ssl(page)
    assertion(m.passed is False, "passed=False")
    assertion(m.value is False, "value=False")


def test_check_ssl_fetch_failure() -> None:
    print("\n[T07] _check_ssl — fetch failure → passed=False + evidence")
    page = MainPage(0, 0.0, 0, "https://x.test/", None, "dns failure", {})
    m = _check_ssl(page)
    assertion(m.passed is False, "passed=False on fetch failure")
    assertion(m.evidence is not None and "fetch failed" in m.evidence, "evidence carries error")


# ─── _check_robots_txt ───────────────────────────────────────────────────

async def test_robots_ok_with_sitemap_ref() -> None:
    print("\n[T08] _check_robots_txt — found+sitemap_ref → passed")

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/robots.txt":
            return httpx.Response(200, text=ROBOTS_OK)
        return httpx.Response(404)

    async with _make_client(handler) as client:
        m = await _check_robots_txt(client, "example.test")

    assertion(m.passed is True, "passed=True")
    assertion(m.value == "found+sitemap_ref", "value=found+sitemap_ref")
    assertion(m.evidence is not None and "sitemap_ref" in m.evidence, "evidence flags sitemap_ref")


async def test_robots_disallow_all() -> None:
    print("\n[T09] _check_robots_txt — disallow_all → passed=False")

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=ROBOTS_DISALLOW_ALL)

    async with _make_client(handler) as client:
        m = await _check_robots_txt(client, "example.test")

    assertion(m.passed is False, "passed=False")
    assertion(m.value == "disallow_all", "value=disallow_all")


async def test_robots_404() -> None:
    print("\n[T10] _check_robots_txt — 404 → passed=False")

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    async with _make_client(handler) as client:
        m = await _check_robots_txt(client, "example.test")

    assertion(m.passed is False, "passed=False on 404")
    assertion(m.value == "missing", "value=missing")


async def test_robots_connection_error() -> None:
    print("\n[T11] _check_robots_txt — connection error")

    def handler(_req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("dns failure")

    async with _make_client(handler) as client:
        m = await _check_robots_txt(client, "example.test")

    assertion(m.passed is False, "passed=False on connect error")
    assertion(m.evidence is not None and "fetch failed" in m.evidence, "evidence carries error")


# ─── _check_sitemap ──────────────────────────────────────────────────────

async def test_sitemap_xml_found() -> None:
    print("\n[T12] _check_sitemap — sitemap.xml found → passed")

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/sitemap.xml":
            return httpx.Response(200, text=SITEMAP_OK)
        return httpx.Response(404)

    async with _make_client(handler) as client:
        m = await _check_sitemap(client, "example.test")

    assertion(m.passed is True, "passed=True")
    assertion(m.value == "https://example.test/sitemap.xml", "value=sitemap.xml URL")


async def test_sitemap_index_fallback() -> None:
    print("\n[T13] _check_sitemap — sitemap.xml 404 → sitemap_index.xml fallback")

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/sitemap_index.xml":
            return httpx.Response(
                200,
                text='<?xml version="1.0"?><sitemapindex></sitemapindex>'
            )
        return httpx.Response(404)

    async with _make_client(handler) as client:
        m = await _check_sitemap(client, "example.test")

    assertion(m.passed is True, "passed=True via fallback")
    assertion(m.value == "https://example.test/sitemap_index.xml", "value=sitemap_index URL")


async def test_sitemap_neither_found() -> None:
    print("\n[T14] _check_sitemap — neither found")

    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with _make_client(handler) as client:
        m = await _check_sitemap(client, "example.test")

    assertion(m.passed is False, "passed=False")
    assertion(m.value is None, "value=None")


# ─── _check_canonical / _check_mobile_viewport ──────────────────────────

def test_canonical_present() -> None:
    print("\n[T15] _check_canonical — link present")
    soup = BeautifulSoup(GOOD_HTML, "lxml")
    m = _check_canonical(soup, None)
    assertion(m.passed is True, "passed=True")
    assertion(m.value == "https://example.test/", "value=canonical href")


def test_canonical_absent() -> None:
    print("\n[T16] _check_canonical — link absent")
    soup = BeautifulSoup(NO_CANONICAL_NO_VIEWPORT_HTML, "lxml")
    m = _check_canonical(soup, None)
    assertion(m.passed is False, "passed=False")
    assertion(m.value is None, "value=None")


def test_canonical_no_soup() -> None:
    print("\n[T17] _check_canonical — soup=None propagates fetch error")
    m = _check_canonical(None, "HTTP 500")
    assertion(m.passed is False, "passed=False")
    assertion(m.evidence is not None and "HTTP 500" in m.evidence, "evidence carries fetch_error")


def test_viewport_with_width() -> None:
    print("\n[T18] _check_mobile_viewport — width= present → passed")
    soup = BeautifulSoup(GOOD_HTML, "lxml")
    m = _check_mobile_viewport(soup, None)
    assertion(m.passed is True, "passed=True")
    assertion(m.value is not None and "width=" in str(m.value), "value contains width=")


def test_viewport_no_width() -> None:
    print("\n[T19] _check_mobile_viewport — viewport without width=")
    soup = BeautifulSoup(VIEWPORT_NO_WIDTH_HTML, "lxml")
    m = _check_mobile_viewport(soup, None)
    assertion(m.passed is False, "passed=False without width=")
    assertion(m.evidence == "width=missing", "evidence=width=missing")


def test_viewport_absent() -> None:
    print("\n[T20] _check_mobile_viewport — meta tag absent")
    soup = BeautifulSoup(NO_CANONICAL_NO_VIEWPORT_HTML, "lxml")
    m = _check_mobile_viewport(soup, None)
    assertion(m.passed is False, "passed=False")
    assertion(m.value is None, "value=None")


# ─── _check_page_speed ───────────────────────────────────────────────────

def test_page_speed_fast() -> None:
    print("\n[T21] _check_page_speed — under threshold passes")
    page = MainPage(200, 250.0, 1024, "https://example.test/", BeautifulSoup("", "lxml"), None, {})
    m = _check_page_speed(page)
    assertion(m.passed is True, "passed=True")
    assertion(m.threshold == PAGE_SPEED_THRESHOLD_MS, "threshold set")
    assertion(m.value == 250.0, "value=elapsed_ms")


def test_page_speed_slow() -> None:
    print("\n[T22] _check_page_speed — over threshold fails")
    page = MainPage(200, 3500.0, 50_000, "https://slow.test/", None, None, {})
    m = _check_page_speed(page)
    assertion(m.passed is False, "passed=False")
    assertion(m.value == 3500.0, "value=3500ms preserved")


def test_page_speed_fetch_error() -> None:
    print("\n[T23] _check_page_speed — fetch failure")
    page = MainPage(0, 0.0, 0, "https://x.test/", None, "dns failure", {})
    m = _check_page_speed(page)
    assertion(m.passed is False, "passed=False")
    assertion(m.value is None, "value=None")


# ─── analyze() 통합 ──────────────────────────────────────────────────────

async def test_analyze_full_happy() -> None:
    print("\n[T24] analyze() — full happy site (모든 메트릭 passed)")

    def handler(req: httpx.Request) -> httpx.Response:
        path = req.url.path
        if path == "/":
            return httpx.Response(200, text=GOOD_HTML)
        if path == "/robots.txt":
            return httpx.Response(200, text=ROBOTS_OK)
        if path == "/sitemap.xml":
            return httpx.Response(200, text=SITEMAP_OK)
        return httpx.Response(404)

    # MockTransport 를 analyze 가 직접 만드는 client 에 주입할 수 없음 →
    # 통합 테스트는 monkey-patch 로 httpx.AsyncClient default transport 교체.
    import app.scoring.technical as tech_mod

    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)

    def mock_async_client(*args, **kwargs):  # noqa: ANN001
        kwargs.pop("transport", None)
        return real_client(transport=transport, **kwargs)

    tech_mod.httpx.AsyncClient = mock_async_client  # type: ignore[assignment]
    try:
        result = await analyze("https://example.test/", AnalysisOptions())
    finally:
        tech_mod.httpx.AsyncClient = real_client  # type: ignore[assignment]

    assertion(len(result.metrics) == 6, "6 metrics returned")
    keys = {m.key for m in result.metrics}
    assertion(keys == {
        "ssl_enabled", "robots_txt", "sitemap_xml",
        "canonical_tag", "mobile_viewport", "page_speed",
    }, "metric keys = 6")
    all_passed = all(m.passed for m in result.metrics)
    assertion(all_passed, "all metrics passed (full happy site)")
    assertion(result.score == 100.0, f"score=100.0 (got {result.score})")


async def test_analyze_full_failure() -> None:
    print("\n[T25] analyze() — total failure (connect error 모든 호출)")

    def handler(_req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("simulated outage")

    import app.scoring.technical as tech_mod

    real_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)

    def mock_async_client(*args, **kwargs):  # noqa: ANN001
        kwargs.pop("transport", None)
        return real_client(transport=transport, **kwargs)

    tech_mod.httpx.AsyncClient = mock_async_client  # type: ignore[assignment]
    try:
        result = await analyze("https://nonexistent.test/", AnalysisOptions())
    finally:
        tech_mod.httpx.AsyncClient = real_client  # type: ignore[assignment]

    assertion(len(result.metrics) == 6, "6 metrics returned even on full failure")
    none_passed = not any(m.passed for m in result.metrics)
    assertion(none_passed, "no metrics passed")
    assertion(result.score == 0.0, f"score=0.0 (got {result.score})")
    # evidence 가 에러 메시지를 보존하는지 검증.
    fail_metrics_with_evidence = [
        m for m in result.metrics if m.evidence and "fetch failed" in m.evidence
    ]
    assertion(len(fail_metrics_with_evidence) >= 4, "≥4 metrics carry 'fetch failed' evidence")


# ─── runner ──────────────────────────────────────────────────────────────

async def main() -> int:
    test_domain_extraction()
    await test_fetch_main_page_200()
    await test_fetch_main_page_404()
    await test_fetch_main_page_connection_error()
    test_check_ssl_https()
    test_check_ssl_http()
    test_check_ssl_fetch_failure()
    await test_robots_ok_with_sitemap_ref()
    await test_robots_disallow_all()
    await test_robots_404()
    await test_robots_connection_error()
    await test_sitemap_xml_found()
    await test_sitemap_index_fallback()
    await test_sitemap_neither_found()
    test_canonical_present()
    test_canonical_absent()
    test_canonical_no_soup()
    test_viewport_with_width()
    test_viewport_no_width()
    test_viewport_absent()
    test_page_speed_fast()
    test_page_speed_slow()
    test_page_speed_fetch_error()
    await test_analyze_full_happy()
    await test_analyze_full_failure()

    print(f"\n=== {len(FAILED)} failed ===" if FAILED else "\n=== ALL TESTS PASSED ===")
    if FAILED:
        for label in FAILED:
            print(f"  - {label}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
