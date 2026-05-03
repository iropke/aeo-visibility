"""Authority 카테고리 v2 단위 테스트 — 외부 의존 ❌ (httpx MockTransport + whois mock).

실행:
    Set-Location backend; $env:PYTHONUTF8="1"; $env:PYTHONPATH="$PWD"
    .venv\\Scripts\\python.exe scripts\\test_authority_v2.py

4 메트릭 (organization_schema / author_entity / citation_metadata /
domain_age) + analyze() 통합 (default options + enable_external_apis +
fetch fail). G5-authority-redesign 청크의 AEO 직접 신호 4종 검증.

mock 패턴:
- httpx.AsyncClient → mock_factory (transport 만 교체).
- whois.whois → MagicMock (creation_date 응답 객체 시뮬레이션).
- asyncio.to_thread 는 monkey-patch ❌ (그대로 동작 — mock whois 가 동기 반환).
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from typing import Callable
from unittest.mock import MagicMock

import httpx
from bs4 import BeautifulSoup

from app.scoring import authority as auth_mod
from app.scoring.authority import (
    CITATION_METADATA_MIN_FIELDS,
    DOMAIN_AGE_MIN_YEARS,
    ORGANIZATION_TYPES,
    PERSON_TYPES,
    _check_author_entity,
    _check_citation_metadata,
    _check_domain_age,
    _check_organization_schema,
    _domain_from_url,
    _iter_jsonld_objects,
    _normalize_types,
    analyze,
)
from app.scoring.schemas import AnalysisOptions


# ─── 픽스처 ─────────────────────────────────────────────────────────────

ORG_FULL_HTML = """<!doctype html>
<html><head>
  <title>Demo Co</title>
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Demo Co",
    "url": "https://demo.test/",
    "sameAs": [
      "https://en.wikipedia.org/wiki/Demo",
      "https://twitter.com/demo",
      "https://www.linkedin.com/company/demo"
    ]
  }
  </script>
</head><body><h1>Demo</h1></body></html>
"""

ORG_SUBTYPE_HTML = """<!doctype html>
<html><head>
  <script type="application/ld+json">
  {"@type": "Corporation", "name": "Acme", "sameAs": "https://twitter.com/acme"}
  </script>
</head><body></body></html>
"""

ORG_NO_SAMEAS_HTML = """<!doctype html>
<html><head>
  <script type="application/ld+json">
  {"@type": "Organization", "name": "Org without sameAs"}
  </script>
</head><body></body></html>
"""

NO_ORG_HTML = """<!doctype html>
<html><head>
  <script type="application/ld+json">
  {"@type": "Article", "headline": "no org"}
  </script>
</head><body></body></html>
"""

GRAPH_ORG_HTML = """<!doctype html>
<html><head>
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@graph": [
      {"@type": "WebPage", "name": "Home"},
      {
        "@type": "Organization",
        "name": "Graph Co",
        "sameAs": ["https://x.com/graph"]
      }
    ]
  }
  </script>
</head><body></body></html>
"""

PERSON_JSONLD_HTML = """<!doctype html>
<html><head>
  <script type="application/ld+json">
  {
    "@type": "Person",
    "name": "Jane Doe",
    "sameAs": ["https://www.linkedin.com/in/janedoe"]
  }
  </script>
</head><body></body></html>
"""

ARTICLE_AUTHOR_DICT_HTML = """<!doctype html>
<html><head>
  <script type="application/ld+json">
  {
    "@type": "Article",
    "headline": "Post",
    "author": {
      "@type": "Person",
      "name": "Bob",
      "sameAs": "https://twitter.com/bob"
    }
  }
  </script>
</head><body></body></html>
"""

ARTICLE_AUTHOR_STRING_HTML = """<!doctype html>
<html><head>
  <script type="application/ld+json">
  {"@type": "Article", "headline": "Post", "author": "Charlie"}
  </script>
</head><body></body></html>
"""

META_AUTHOR_ONLY_HTML = """<!doctype html>
<html><head>
  <meta name="author" content="Alice">
</head><body></body></html>
"""

NO_AUTHOR_HTML = """<!doctype html>
<html><head><title>nothing</title></head><body><p>x</p></body></html>
"""

CITATION_FULL_HTML = """<!doctype html>
<html><head>
  <script type="application/ld+json">
  {
    "@type": "NewsArticle",
    "headline": "Post",
    "datePublished": "2024-01-01T00:00:00Z",
    "dateModified": "2024-06-01T00:00:00Z",
    "author": {"@type": "Person", "name": "X"},
    "publisher": {"@type": "Organization", "name": "Y"}
  }
  </script>
</head><body></body></html>
"""

CITATION_PARTIAL_HTML = """<!doctype html>
<html><head>
  <meta property="article:published_time" content="2024-01-01">
  <meta name="author" content="Z">
  <meta property="article:modified_time" content="2024-06-01">
</head><body></body></html>
"""

CITATION_TOO_FEW_HTML = """<!doctype html>
<html><head>
  <meta name="author" content="Z">
</head><body></body></html>
"""


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


# ─── 어설션 헬퍼 ─────────────────────────────────────────────────────────

FAILED: list[str] = []


def _check(label: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    suffix = f" — {detail}" if detail and not cond else ""
    print(f"  [{status}] {label}{suffix}")
    if not cond:
        FAILED.append(label)


# ─── _domain_from_url + _normalize_types + _iter_jsonld_objects ──────────

def test_domain_from_url():
    print("\n== _domain_from_url ==")
    _check("T01 https://example.com → example.com",
           _domain_from_url("https://example.com") == "example.com")
    _check("T02 https://www.example.com/p → example.com",
           _domain_from_url("https://www.example.com/p") == "example.com")


def test_normalize_types():
    print("\n== _normalize_types ==")
    _check("T03 string → [string]",
           _normalize_types("Organization") == ["Organization"])
    _check("T04 list → list (str only)",
           _normalize_types(["A", "B", 1, None]) == ["A", "B"])
    _check("T05 None → []", _normalize_types(None) == [])


def test_iter_jsonld_objects():
    print("\n== _iter_jsonld_objects ==")
    items = list(_iter_jsonld_objects(_soup(ORG_FULL_HTML)))
    _check("T06 single dict yields 1 item",
           len(items) == 1 and items[0].get("@type") == "Organization")

    items = list(_iter_jsonld_objects(_soup(GRAPH_ORG_HTML)))
    _check("T07 @graph → flatten 2 items",
           len(items) == 2 and any(i.get("@type") == "Organization" for i in items))

    invalid_html = '<html><head><script type="application/ld+json">{ broken</script></head></html>'
    items = list(_iter_jsonld_objects(_soup(invalid_html)))
    _check("T08 invalid JSON → skipped (no exception)", items == [])


# ─── _check_organization_schema ────────────────────────────────────────

def test_org_schema_full():
    print("\n== _check_organization_schema — full ==")
    m = _check_organization_schema(_soup(ORG_FULL_HTML), None)
    _check("T09 Organization + 3 sameAs → passed",
           m.passed is True and m.value == 3,
           detail=f"value={m.value}, evidence={m.evidence}")
    _check("T10 evidence has type + sameAs count",
           "Organization" in (m.evidence or "") and "sameAs=3" in (m.evidence or ""))


def test_org_schema_subtype():
    print("\n== _check_organization_schema — sub-type Corporation ==")
    m = _check_organization_schema(_soup(ORG_SUBTYPE_HTML), None)
    _check("T11 Corporation + 1 sameAs → passed",
           m.passed is True and m.value == 1,
           detail=f"value={m.value}")
    _check("T12 sub-type recognized in evidence",
           "Corporation" in (m.evidence or ""))


def test_org_schema_no_sameas():
    print("\n== _check_organization_schema — Organization without sameAs ==")
    m = _check_organization_schema(_soup(ORG_NO_SAMEAS_HTML), None)
    _check("T13 Organization but sameAs=0 → fail",
           m.passed is False and m.value == 0)


def test_org_schema_absent():
    print("\n== _check_organization_schema — no Organization ==")
    m = _check_organization_schema(_soup(NO_ORG_HTML), None)
    _check("T14 only Article (no Organization) → fail",
           m.passed is False and m.value == 0)
    _check("T15 evidence indicates no Organization found",
           "no JSON-LD Organization" in (m.evidence or ""))


def test_org_schema_graph():
    print("\n== _check_organization_schema — @graph ==")
    m = _check_organization_schema(_soup(GRAPH_ORG_HTML), None)
    _check("T16 Organization inside @graph → passed",
           m.passed is True and m.value == 1)


def test_org_schema_no_soup():
    print("\n== _check_organization_schema — soup=None ==")
    m = _check_organization_schema(None, "HTTP 500")
    _check("T17 no soup → fail with fetch_error",
           m.passed is False and "HTTP 500" in (m.evidence or ""))


# ─── _check_author_entity ─────────────────────────────────────────────

def test_author_jsonld_person():
    print("\n== _check_author_entity — JSON-LD Person ==")
    m = _check_author_entity(_soup(PERSON_JSONLD_HTML), None)
    _check("T18 Person → passed",
           m.passed is True and "jsonld_person" in (m.evidence or ""),
           detail=f"evidence={m.evidence}")
    _check("T19 author name preserved", "Jane Doe" in (m.value or ""))


def test_author_article_dict():
    print("\n== _check_author_entity — Article.author dict ==")
    m = _check_author_entity(_soup(ARTICLE_AUTHOR_DICT_HTML), None)
    _check("T20 Article + author dict → passed",
           m.passed is True and "jsonld_article_author" in (m.evidence or ""))
    _check("T21 author name=Bob preserved", "Bob" in (m.value or ""))


def test_author_article_string():
    print("\n== _check_author_entity — Article.author string ==")
    m = _check_author_entity(_soup(ARTICLE_AUTHOR_STRING_HTML), None)
    _check("T22 Article + author string → passed",
           m.passed is True and "Charlie" in (m.value or ""))


def test_author_meta_only():
    print("\n== _check_author_entity — meta[name=author] only ==")
    m = _check_author_entity(_soup(META_AUTHOR_ONLY_HTML), None)
    _check("T23 meta author → passed",
           m.passed is True and "meta_author" in (m.evidence or ""))


def test_author_absent():
    print("\n== _check_author_entity — none ==")
    m = _check_author_entity(_soup(NO_AUTHOR_HTML), None)
    _check("T24 no author signals → fail",
           m.passed is False and m.value is None)


def test_author_no_soup():
    print("\n== _check_author_entity — soup=None ==")
    m = _check_author_entity(None, "HTTP 404")
    _check("T25 no soup → fail with fetch_error",
           m.passed is False and "HTTP 404" in (m.evidence or ""))


# ─── _check_citation_metadata ─────────────────────────────────────────

def test_citation_full_jsonld():
    print("\n== _check_citation_metadata — 4 fields in JSON-LD ==")
    m = _check_citation_metadata(_soup(CITATION_FULL_HTML), None)
    _check("T26 4 fields all present → passed (count=4)",
           m.passed is True and m.value == 4,
           detail=f"value={m.value}, evidence={m.evidence}")


def test_citation_partial_meta():
    print("\n== _check_citation_metadata — 3 fields in meta ==")
    m = _check_citation_metadata(_soup(CITATION_PARTIAL_HTML), None)
    _check(f"T27 3 fields via meta → passed (>={CITATION_METADATA_MIN_FIELDS})",
           m.passed is True and m.value == 3,
           detail=f"value={m.value}, evidence={m.evidence}")


def test_citation_too_few():
    print("\n== _check_citation_metadata — only 1 field ==")
    m = _check_citation_metadata(_soup(CITATION_TOO_FEW_HTML), None)
    _check(f"T28 only author (1 field) → fail (<{CITATION_METADATA_MIN_FIELDS})",
           m.passed is False and m.value == 1)


def test_citation_none():
    print("\n== _check_citation_metadata — 0 fields ==")
    m = _check_citation_metadata(_soup(NO_AUTHOR_HTML), None)
    _check("T29 nothing → fail (count=0)",
           m.passed is False and m.value == 0)


def test_citation_no_soup():
    print("\n== _check_citation_metadata — soup=None ==")
    m = _check_citation_metadata(None, "HTTP 503")
    _check("T30 no soup → fail with fetch_error",
           m.passed is False and "HTTP 503" in (m.evidence or ""))


# ─── _check_domain_age ────────────────────────────────────────────────

async def test_domain_age_disabled():
    print("\n== _check_domain_age — enable_external_apis=False (default) ==")
    m = await _check_domain_age("https://example.com", AnalysisOptions())
    _check("T31 default options → stub with 'external_apis disabled'",
           m.passed is False and "external_apis disabled" in (m.evidence or ""),
           detail=f"evidence={m.evidence}")


async def test_domain_age_old():
    print("\n== _check_domain_age — old domain (5y) ==")
    five_years_ago = datetime.now(timezone.utc) - timedelta(days=int(365.25 * 5))
    original_whois = auth_mod.whois
    fake_whois = MagicMock()
    fake_whois.whois = MagicMock(
        return_value=MagicMock(creation_date=five_years_ago)
    )
    auth_mod.whois = fake_whois
    try:
        opts = AnalysisOptions(enable_external_apis=True)
        m = await _check_domain_age("https://old.com", opts)
        _check("T32 5y old → passed (>=1y)",
               m.passed is True and isinstance(m.value, float) and m.value >= 1.0,
               detail=f"value={m.value}, evidence={m.evidence}")
    finally:
        auth_mod.whois = original_whois


async def test_domain_age_young():
    print("\n== _check_domain_age — young domain (3 months) ==")
    three_months_ago = datetime.now(timezone.utc) - timedelta(days=90)
    original_whois = auth_mod.whois
    fake_whois = MagicMock()
    fake_whois.whois = MagicMock(
        return_value=MagicMock(creation_date=three_months_ago)
    )
    auth_mod.whois = fake_whois
    try:
        opts = AnalysisOptions(enable_external_apis=True)
        m = await _check_domain_age("https://new.com", opts)
        _check("T33 90d old → fail (<1y)",
               m.passed is False and isinstance(m.value, float) and m.value < 1.0,
               detail=f"value={m.value}")
    finally:
        auth_mod.whois = original_whois


async def test_domain_age_list():
    print("\n== _check_domain_age — creation_date as list ==")
    five_years_ago = datetime.now(timezone.utc) - timedelta(days=int(365.25 * 5))
    later = datetime.now(timezone.utc) - timedelta(days=int(365.25 * 3))
    original_whois = auth_mod.whois
    fake_whois = MagicMock()
    fake_whois.whois = MagicMock(
        return_value=MagicMock(creation_date=[five_years_ago, later])
    )
    auth_mod.whois = fake_whois
    try:
        opts = AnalysisOptions(enable_external_apis=True)
        m = await _check_domain_age("https://list.com", opts)
        _check("T34 list[datetime] → first element used → passed",
               m.passed is True and m.value >= 4.0,  # 5y rounded
               detail=f"value={m.value}")
    finally:
        auth_mod.whois = original_whois


async def test_domain_age_exception():
    print("\n== _check_domain_age — WHOIS exception ==")
    original_whois = auth_mod.whois
    fake_whois = MagicMock()
    fake_whois.whois = MagicMock(side_effect=RuntimeError("connection refused"))
    auth_mod.whois = fake_whois
    try:
        opts = AnalysisOptions(enable_external_apis=True)
        m = await _check_domain_age("https://err.com", opts)
        _check("T35 exception → fail with WHOIS evidence",
               m.passed is False and "WHOIS lookup failed" in (m.evidence or ""))
    finally:
        auth_mod.whois = original_whois


async def test_domain_age_none():
    print("\n== _check_domain_age — creation_date=None ==")
    original_whois = auth_mod.whois
    fake_whois = MagicMock()
    fake_whois.whois = MagicMock(return_value=MagicMock(creation_date=None))
    auth_mod.whois = fake_whois
    try:
        opts = AnalysisOptions(enable_external_apis=True)
        m = await _check_domain_age("https://noinfo.com", opts)
        _check("T36 creation_date=None → fail with 'not available' evidence",
               m.passed is False and "not available" in (m.evidence or ""))
    finally:
        auth_mod.whois = original_whois


async def test_domain_age_tz_naive():
    print("\n== _check_domain_age — tz-naive datetime normalized to UTC ==")
    naive = datetime.utcnow() - timedelta(days=int(365.25 * 2))
    original_whois = auth_mod.whois
    fake_whois = MagicMock()
    fake_whois.whois = MagicMock(return_value=MagicMock(creation_date=naive))
    auth_mod.whois = fake_whois
    try:
        opts = AnalysisOptions(enable_external_apis=True)
        m = await _check_domain_age("https://naive.com", opts)
        _check("T37 tz-naive → normalized → passed (2y)",
               m.passed is True and m.value >= 1.5,
               detail=f"value={m.value}")
    finally:
        auth_mod.whois = original_whois


# ─── analyze() 통합 ────────────────────────────────────────────────────

def _make_http_factory(html: str = ORG_FULL_HTML, status: int = 200):
    """httpx.AsyncClient mock factory — transport 만 교체."""
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
    def handler(request: httpx.Request) -> httpx.Response:
        raise error
    transport = httpx.MockTransport(handler)
    real_async_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_async_client(*args, **kwargs)
    return factory


# 모든 4종 신호가 풍부한 HTML — 통합 happy 용.
ANALYZE_HAPPY_HTML = """<!doctype html>
<html><head>
  <title>Demo Co</title>
  <meta name="author" content="Jane Doe">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Organization",
        "name": "Demo Co",
        "sameAs": [
          "https://en.wikipedia.org/wiki/Demo",
          "https://twitter.com/demo"
        ],
        "publisher": {"@type": "Organization", "name": "Demo Co"}
      },
      {
        "@type": "NewsArticle",
        "headline": "About",
        "datePublished": "2024-01-01T00:00:00Z",
        "dateModified": "2024-06-01T00:00:00Z",
        "author": {"@type": "Person", "name": "Jane Doe"}
      }
    ]
  }
  </script>
</head><body><h1>Demo</h1></body></html>
"""


async def test_analyze_default_options():
    print("\n== analyze() — default options (external_apis OFF) ==")
    original_httpx = httpx.AsyncClient
    httpx.AsyncClient = _make_http_factory(ANALYZE_HAPPY_HTML)
    try:
        result = await analyze("https://demo.test/", AnalysisOptions())
        _check("T38 4 metrics returned",
               len(result.metrics) == 4)
        keyed = {m.key: m for m in result.metrics}
        _check("T39 metric keys = 4 신규 키",
               set(keyed.keys()) == {
                   "organization_schema", "author_entity",
                   "citation_metadata", "domain_age",
               })
        _check("T40 organization_schema passed",
               keyed["organization_schema"].passed is True)
        _check("T41 author_entity passed",
               keyed["author_entity"].passed is True)
        _check("T42 citation_metadata passed",
               keyed["citation_metadata"].passed is True)
        _check("T43 domain_age stub (external_apis OFF)",
               keyed["domain_age"].passed is False
               and "external_apis disabled" in (keyed["domain_age"].evidence or ""))
        # 0.35 + 0.25 + 0.20 = 0.80 → 80.0
        _check("T44 score = 80.0 (3/4 passed, domain_age stub)",
               abs(result.score - 80.0) < 0.01,
               detail=f"score={result.score}")
    finally:
        httpx.AsyncClient = original_httpx


async def test_analyze_full_happy_with_whois():
    print("\n== analyze() — full happy with enable_external_apis=True ==")
    five_years_ago = datetime.now(timezone.utc) - timedelta(days=int(365.25 * 5))
    original_httpx = httpx.AsyncClient
    original_whois = auth_mod.whois
    httpx.AsyncClient = _make_http_factory(ANALYZE_HAPPY_HTML)
    fake_whois = MagicMock()
    fake_whois.whois = MagicMock(
        return_value=MagicMock(creation_date=five_years_ago)
    )
    auth_mod.whois = fake_whois
    try:
        opts = AnalysisOptions(enable_external_apis=True)
        result = await analyze("https://demo.test/", opts)
        _check("T45 all 4 metrics passed",
               all(m.passed for m in result.metrics),
               detail=f"score={result.score}")
        _check("T46 score = 100.0",
               abs(result.score - 100.0) < 0.01,
               detail=f"score={result.score}")
    finally:
        httpx.AsyncClient = original_httpx
        auth_mod.whois = original_whois


async def test_analyze_fetch_fail():
    print("\n== analyze() — fetch fail → 3 unavailable + domain_age stub ==")
    original_httpx = httpx.AsyncClient
    httpx.AsyncClient = _make_http_factory_error(httpx.ConnectError("dns fail"))
    try:
        result = await analyze("https://x.test/", AnalysisOptions())
        _check("T47 4 metrics returned",
               len(result.metrics) == 4)
        keyed = {m.key: m for m in result.metrics}
        for k in ("organization_schema", "author_entity", "citation_metadata"):
            _check(f"T48 {k} unavailable evidence",
                   keyed[k].passed is False
                   and "main page unavailable" in (keyed[k].evidence or ""))
        _check("T49 domain_age still stub (external_apis OFF)",
               keyed["domain_age"].passed is False
               and "external_apis disabled" in (keyed["domain_age"].evidence or ""))
        _check("T50 score = 0",
               result.score == 0.0,
               detail=f"score={result.score}")
    finally:
        httpx.AsyncClient = original_httpx


async def test_analyze_partial_signals():
    print("\n== analyze() — partial: org+citation pass, author fail, domain stub ==")
    original_httpx = httpx.AsyncClient
    # Organization + sameAs + 4 citation fields, but no author signals.
    partial_html = """<!doctype html>
<html><head>
  <script type="application/ld+json">
  {
    "@type": "Organization",
    "name": "Demo",
    "sameAs": ["https://x.com/demo"],
    "datePublished": "2024-01-01",
    "dateModified": "2024-06-01",
    "publisher": "Demo Co"
  }
  </script>
</head><body></body></html>
"""
    httpx.AsyncClient = _make_http_factory(partial_html)
    try:
        result = await analyze("https://demo.test/", AnalysisOptions())
        keyed = {m.key: m for m in result.metrics}
        # author 는 publisher 가 있어도 별도. publisher 는 citation 의 4 필드 중
        # 하나로만 카운트되고 author_entity 는 별도 신호 (Person/Article.author/meta).
        # → author_entity 는 fail.
        _check("T51 organization_schema passed",
               keyed["organization_schema"].passed is True)
        _check("T52 author_entity fail (no author signal)",
               keyed["author_entity"].passed is False)
        # citation: datePublished + dateModified + author (의 string) + publisher = 4
        # ⚠️ 실제로는 author 필드가 obj 에 없음. publisher + datePublished + dateModified = 3
        # → passed (>=3).
        _check("T53 citation_metadata passed (>=3 fields)",
               keyed["citation_metadata"].passed is True
               and keyed["citation_metadata"].value >= 3,
               detail=f"value={keyed['citation_metadata'].value}")
        _check("T54 domain_age stub",
               keyed["domain_age"].passed is False)
        # 0.35 (org) + 0.20 (citation) = 0.55 → 55.0
        _check("T55 score = 55.0",
               abs(result.score - 55.0) < 0.01,
               detail=f"score={result.score}")
    finally:
        httpx.AsyncClient = original_httpx


# ─── runner ────────────────────────────────────────────────────────────

async def main() -> int:
    test_domain_from_url()
    test_normalize_types()
    test_iter_jsonld_objects()
    test_org_schema_full()
    test_org_schema_subtype()
    test_org_schema_no_sameas()
    test_org_schema_absent()
    test_org_schema_graph()
    test_org_schema_no_soup()
    test_author_jsonld_person()
    test_author_article_dict()
    test_author_article_string()
    test_author_meta_only()
    test_author_absent()
    test_author_no_soup()
    test_citation_full_jsonld()
    test_citation_partial_meta()
    test_citation_too_few()
    test_citation_none()
    test_citation_no_soup()
    await test_domain_age_disabled()
    await test_domain_age_old()
    await test_domain_age_young()
    await test_domain_age_list()
    await test_domain_age_exception()
    await test_domain_age_none()
    await test_domain_age_tz_naive()
    await test_analyze_default_options()
    await test_analyze_full_happy_with_whois()
    await test_analyze_fetch_fail()
    await test_analyze_partial_signals()

    print("\n" + "=" * 60)
    if FAILED:
        print(f"FAILED: {len(FAILED)} cases")
        for label in FAILED:
            print(f"  - {label}")
        return 1
    print("All cases PASS — Authority AEO 4 metrics (G5-authority-redesign) verified.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
