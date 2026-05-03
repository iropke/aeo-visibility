"""Authority 카테고리 — AEO 직접 신호 메트릭 (G5-authority-redesign 재정의).

SPEC §7-1 메트릭 키 4종 (analysis_version v2.0). 2026-05-03 G5-authority-
redesign 청크에서 v1 SEO 휴리스틱 (domain_age/social_links/contact_info/
security_headers) 4종을 AEO 직접 신호 4종으로 교체.

- ``organization_schema`` (0.35): JSON-LD ``@type: Organization`` (또는 sub-type) +
  ``sameAs`` URL ≥1. Knowledge Graph 가 brand entity 인식 → LLM 학습 시
  brand-domain 연결의 강한 신호.
- ``author_entity`` (0.25): JSON-LD ``Person`` / ``Article.author`` 또는
  ``<meta name="author">``. E-E-A-T (Experience/Expertise) 직접 표시.
- ``citation_metadata`` (0.20): ``datePublished`` / ``dateModified`` / ``author`` /
  ``publisher`` 4종 중 ≥3 발견. AI Overview/Citation 가 인용할 때 활용.
- ``domain_age`` (0.20): WHOIS creation_date ≥1년. ``enable_external_apis=False``
  (기본) 면 stub. WHOIS 호출은 ``asyncio.to_thread`` (python-whois 동기 라이브러리).

Phase 1 무료 베타 정합 — 외부 API 의존 메트릭 (wikipedia_mention,
external_backlinks) 은 Phase 2 add-on 으로 미룸. organization_schema /
author_entity / citation_metadata 3종은 main page HTML 만으로 측정.

mock 가능 구조: ``whois`` 모듈을 module-level import → 테스트가
``authority_mod.whois.whois = MagicMock(...)`` 로 교체 가능.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
import whois  # python-whois (동기 라이브러리, asyncio.to_thread 로 호출)
from bs4 import BeautifulSoup

from app.scoring._common import (
    build_category_metrics,
    build_metric,
    fetch_main_page,
)
from app.scoring.schemas import AnalysisOptions, CategoryMetrics, MetricResult
from app.scoring.weights import AUTHORITY_METRIC_WEIGHTS


log = logging.getLogger(__name__)

CATEGORY_NAME = "authority"

# ─── 임계값 (의도된 v2 정책) ───

# domain_age binary 임계값 — v1 의 50점 (1+ year) 경계.
DOMAIN_AGE_MIN_YEARS: float = 1.0

# citation_metadata 4종 중 발견해야 하는 최소 개수 — ≥3 = "AI 인용 친화적".
CITATION_METADATA_MIN_FIELDS: int = 3

# Organization 인정 후보 (Schema.org 의 Organization 및 주요 sub-types).
# 단일 dict 와 sub-type 모두 인정 — LocalBusiness 등 sub-type 도 brand entity 신호.
ORGANIZATION_TYPES: frozenset[str] = frozenset({
    "Organization",
    "Corporation",
    "LocalBusiness",
    "NewsMediaOrganization",
    "EducationalOrganization",
    "GovernmentOrganization",
    "NGO",
    "PerformingGroup",
    "SportsOrganization",
    "OnlineBusiness",
    "MedicalBusiness",
})

# author Person 인정 후보.
PERSON_TYPES: frozenset[str] = frozenset({"Person"})

# citation_metadata 필드 - JSON-LD 키와 메타 태그 후보.
CITATION_FIELDS_JSONLD: tuple[str, ...] = (
    "datePublished", "dateModified", "author", "publisher",
)
CITATION_FIELDS_META: dict[str, tuple[str, ...]] = {
    # field → (meta name/property) 후보 리스트 — 어느 하나라도 발견되면 ✓.
    "datePublished": ("article:published_time", "datePublished"),
    "dateModified":  ("article:modified_time", "og:updated_time", "dateModified"),
    "author":        ("author", "article:author"),
    "publisher":     ("publisher", "article:publisher"),
}


def _unavailable(metric_key: str, weight: float, fetch_error: str | None) -> MetricResult:
    """soup=None 일 때 공통 evidence — fetch 실패 메시지 보존.

    organization_schema / author_entity / citation_metadata 3 메트릭 공통.
    domain_age 는 main page 와 무관 (WHOIS 호출 별도) 이므로 별도 처리.
    """
    return build_metric(
        CATEGORY_NAME, metric_key, weight,
        value=None, passed=False,
        evidence=f"main page unavailable: {fetch_error or 'no soup'}",
    )


def _domain_from_url(url: str) -> str:
    """URL → 도메인 (www. 제거, lower-case). WHOIS 호출 인수."""
    parsed = urlparse(url)
    host = (parsed.netloc or parsed.path or "").lower().strip("/")
    return host[4:] if host.startswith("www.") else host


def _iter_jsonld_objects(soup: BeautifulSoup):
    """``<script type="application/ld+json">`` 안의 dict 들을 평면 iterate.

    JSON-LD 는 단일 dict / list of dict / @graph 배열 모두 가능 → 평면화.
    yield 되는 항목은 모두 dict.
    """
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, AttributeError, TypeError):
            continue
        if isinstance(data, dict):
            graph = data.get("@graph")
            if isinstance(graph, list):
                for item in graph:
                    if isinstance(item, dict):
                        yield item
            else:
                yield data
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    yield item


def _normalize_types(value) -> list[str]:
    """``@type`` 값을 list[str] 로 정규화 — Schema.org 는 단일/배열 모두 허용."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [t for t in value if isinstance(t, str)]
    return []


def _check_organization_schema(
    soup: BeautifulSoup | None, fetch_error: str | None
) -> MetricResult:
    """organization_schema — JSON-LD Organization (또는 sub-type) + sameAs ≥1."""
    weight = AUTHORITY_METRIC_WEIGHTS["organization_schema"]
    if soup is None:
        return _unavailable("organization_schema", weight, fetch_error)

    org_types_found: list[str] = []
    sameas_urls: list[str] = []
    for obj in _iter_jsonld_objects(soup):
        types = _normalize_types(obj.get("@type"))
        matched = [t for t in types if t in ORGANIZATION_TYPES]
        if not matched:
            continue
        org_types_found.extend(matched)
        same = obj.get("sameAs")
        if isinstance(same, str):
            sameas_urls.append(same)
        elif isinstance(same, list):
            sameas_urls.extend(s for s in same if isinstance(s, str))

    if not org_types_found:
        return build_metric(
            CATEGORY_NAME, "organization_schema", weight,
            value=0, passed=False,
            threshold=1.0,
            evidence="no JSON-LD Organization (or sub-type) found",
        )

    sameas_count = len(sameas_urls)
    passed = sameas_count >= 1
    types_summary = ",".join(sorted(set(org_types_found))[:3])
    sameas_preview = ",".join(sameas_urls[:3]) + ("..." if sameas_count > 3 else "")
    return build_metric(
        CATEGORY_NAME, "organization_schema", weight,
        value=sameas_count, passed=passed,
        threshold=1.0,
        evidence=(
            f"types={types_summary};sameAs={sameas_count}"
            + (f";urls={sameas_preview}" if sameas_count else "")
        ),
    )


def _check_author_entity(
    soup: BeautifulSoup | None, fetch_error: str | None
) -> MetricResult:
    """author_entity — JSON-LD Person / Article.author 또는 meta[name=author]."""
    weight = AUTHORITY_METRIC_WEIGHTS["author_entity"]
    if soup is None:
        return _unavailable("author_entity", weight, fetch_error)

    sources: list[str] = []
    author_names: list[str] = []
    sameas_urls: list[str] = []

    for obj in _iter_jsonld_objects(soup):
        types = _normalize_types(obj.get("@type"))
        # 1) 직접 Person.
        if any(t in PERSON_TYPES for t in types):
            sources.append("jsonld_person")
            name = obj.get("name")
            if isinstance(name, str):
                author_names.append(name)
            same = obj.get("sameAs")
            if isinstance(same, str):
                sameas_urls.append(same)
            elif isinstance(same, list):
                sameas_urls.extend(s for s in same if isinstance(s, str))
        # 2) Article/BlogPosting 의 author 필드 (Person dict 또는 string).
        author_field = obj.get("author")
        if isinstance(author_field, dict):
            sources.append("jsonld_article_author")
            name = author_field.get("name")
            if isinstance(name, str):
                author_names.append(name)
            same = author_field.get("sameAs")
            if isinstance(same, str):
                sameas_urls.append(same)
            elif isinstance(same, list):
                sameas_urls.extend(s for s in same if isinstance(s, str))
        elif isinstance(author_field, str) and author_field.strip():
            sources.append("jsonld_article_author")
            author_names.append(author_field.strip())

    # 3) <meta name="author"> 보완.
    meta_author = soup.find("meta", attrs={"name": "author"})
    if meta_author:
        content = (meta_author.get("content") or "").strip()
        if content:
            sources.append("meta_author")
            author_names.append(content)

    if not sources:
        return build_metric(
            CATEGORY_NAME, "author_entity", weight,
            value=None, passed=False,
            evidence="no Person JSON-LD / Article.author / meta[name=author]",
        )

    sources_uniq = sorted(set(sources))
    names_summary = ",".join(author_names[:2]) if author_names else "(unnamed)"
    return build_metric(
        CATEGORY_NAME, "author_entity", weight,
        value=names_summary, passed=True,
        evidence=(
            f"sources={','.join(sources_uniq)};name={names_summary};"
            f"sameAs={len(sameas_urls)}"
        ),
    )


def _check_citation_metadata(
    soup: BeautifulSoup | None, fetch_error: str | None
) -> MetricResult:
    """citation_metadata — datePublished/dateModified/author/publisher 4종 중 ≥3 발견.

    JSON-LD 와 메타 태그 양쪽에서 검색 — 어느 쪽에서든 발견되면 그 필드 ✓.
    """
    weight = AUTHORITY_METRIC_WEIGHTS["citation_metadata"]
    if soup is None:
        return _unavailable("citation_metadata", weight, fetch_error)

    found: set[str] = set()

    # 1) JSON-LD lookup.
    for obj in _iter_jsonld_objects(soup):
        for field in CITATION_FIELDS_JSONLD:
            if field in found:
                continue
            value = obj.get(field)
            # truthy: 비어있지 않은 string/dict/list 모두 인정.
            if value:
                found.add(field)

    # 2) 메타 태그 보완.
    for field, candidates in CITATION_FIELDS_META.items():
        if field in found:
            continue
        for cand in candidates:
            meta = soup.find("meta", attrs={"property": cand}) or soup.find(
                "meta", attrs={"name": cand}
            )
            if meta and (meta.get("content") or "").strip():
                found.add(field)
                break

    count = len(found)
    passed = count >= CITATION_METADATA_MIN_FIELDS
    summary = ",".join(sorted(found)) if found else "(none)"
    return build_metric(
        CATEGORY_NAME, "citation_metadata", weight,
        value=count, passed=passed,
        threshold=float(CITATION_METADATA_MIN_FIELDS),
        evidence=(
            f"found=[{summary}];count={count}/{len(CITATION_FIELDS_JSONLD)};"
            f"min={CITATION_METADATA_MIN_FIELDS}"
        ),
    )


async def _check_domain_age(
    url: str, options: AnalysisOptions
) -> MetricResult:
    """domain_age — WHOIS creation_date ≥1년. enable_external_apis=False 면 stub.

    python-whois 는 동기 라이브러리 → ``asyncio.to_thread`` 로 호출 (Python 3.9+).
    응답 객체의 ``creation_date`` 는 datetime / list[datetime] / None 모두 가능.
    """
    weight = AUTHORITY_METRIC_WEIGHTS["domain_age"]
    if not options.enable_external_apis:
        return build_metric(
            CATEGORY_NAME, "domain_age", weight,
            value=None, passed=False,
            threshold=DOMAIN_AGE_MIN_YEARS,
            evidence="external_apis disabled (set enable_external_apis=True for WHOIS)",
        )

    domain = _domain_from_url(url)
    if not domain:
        return build_metric(
            CATEGORY_NAME, "domain_age", weight,
            value=None, passed=False,
            threshold=DOMAIN_AGE_MIN_YEARS,
            evidence=f"could not extract domain from url={url[:60]}",
        )

    try:
        result = await asyncio.to_thread(whois.whois, domain)
        creation = getattr(result, "creation_date", None)
    except Exception as exc:  # noqa: BLE001
        return build_metric(
            CATEGORY_NAME, "domain_age", weight,
            value=None, passed=False,
            threshold=DOMAIN_AGE_MIN_YEARS,
            evidence=f"WHOIS lookup failed: {str(exc)[:100]}",
        )

    # creation_date 는 datetime / list[datetime] / None.
    if isinstance(creation, list):
        creation = creation[0] if creation else None
    if not isinstance(creation, datetime):
        return build_metric(
            CATEGORY_NAME, "domain_age", weight,
            value=None, passed=False,
            threshold=DOMAIN_AGE_MIN_YEARS,
            evidence="WHOIS creation_date not available in response",
        )

    # tz-naive → UTC 정규화 (WHOIS 응답이 종종 tz-naive).
    if creation.tzinfo is None:
        creation = creation.replace(tzinfo=timezone.utc)

    age_days = (datetime.now(timezone.utc) - creation).days
    age_years = round(age_days / 365.25, 1)
    passed = age_years >= DOMAIN_AGE_MIN_YEARS
    return build_metric(
        CATEGORY_NAME, "domain_age", weight,
        value=age_years, passed=passed,
        threshold=DOMAIN_AGE_MIN_YEARS,
        evidence=(
            f"creation={creation.date().isoformat()};age={age_years}y;"
            f"threshold={DOMAIN_AGE_MIN_YEARS}y"
        ),
    )


async def analyze(url: str, options: AnalysisOptions) -> CategoryMetrics:
    """Authority 카테고리 메트릭 분석 (실측, G5-authority-redesign 청크).

    Phase 1 AEO 직접 신호 4종:
    - organization_schema / author_entity / citation_metadata: main page HTML
    - domain_age: WHOIS (``enable_external_apis=True`` 일 때만)

    main page fetch 실패 시 schema/author/citation 3 메트릭은 unavailable
    evidence + passed=False. domain_age 는 ``enable_external_apis`` 분기에
    따라 stub 또는 실 호출 (main page 와 무관).

    Args:
        url: 자사/경쟁사 사이트 URL.
        options: ``AnalysisOptions`` — timeout / user_agent / enable_external_apis.

    Returns:
        ``CategoryMetrics`` — 4 MetricResult + score 0~100.
    """
    headers = {
        "User-Agent": options.user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    timeout = httpx.Timeout(options.timeout_seconds)

    async with httpx.AsyncClient(
        headers=headers, follow_redirects=True, timeout=timeout, verify=True,
    ) as client:
        main_page = await fetch_main_page(client, url)

    soup = main_page.soup
    err = main_page.error

    metrics = [
        _check_organization_schema(soup, err),
        _check_author_entity(soup, err),
        _check_citation_metadata(soup, err),
        await _check_domain_age(url, options),
    ]
    return build_category_metrics(metrics)
