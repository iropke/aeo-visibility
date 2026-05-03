"""Technical 카테고리 — SSL / robots.txt / sitemap / canonical / mobile / page speed.

SPEC §7-1 메트릭 키 6종 (analysis_version v2.0). G5 Technical 청크에서 v1 측정 로직
(``app.scoring.v1.technical``)을 표준 스키마로 옮김.

각 메트릭은 binary ``passed`` + raw ``value``/``evidence`` 보존 — 시계열 디버그 가능.
측정 실패(타임아웃/HTTP 에러)는 passed=False + evidence 에 에러 메시지. 한 메트릭
실패가 다른 메트릭에 전파 ❌ (각자 독립 try/except).

외부 API 의존 ❌ — main page + robots.txt + sitemap.xml HTTP fetch 만. PSI 같은
외부 API 는 ``AnalysisOptions.enable_external_apis=True`` 도입 후 별도 청크.
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.scoring._common import (
    MainPage,
    build_category_metrics,
    build_metric,
    fetch_main_page,
)
from app.scoring.schemas import AnalysisOptions, CategoryMetrics, MetricResult
from app.scoring.weights import TECHNICAL_METRIC_WEIGHTS


log = logging.getLogger(__name__)

CATEGORY_NAME = "technical"

# page_speed binary 임계값 — v1 의 70 점 경계 (< 2000ms) 와 동일.
PAGE_SPEED_THRESHOLD_MS: float = 2000.0


def _domain_from_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.hostname:
        return parsed.hostname
    # bare domain (scheme 없음) — '/' 앞 부분.
    return url.split("/", 1)[0]


def _check_ssl(main_page: MainPage) -> MetricResult:
    """ssl_enabled — fetch 성공한 final_url 이 https:// 로 시작하면 passed."""
    weight = TECHNICAL_METRIC_WEIGHTS["ssl_enabled"]
    if main_page.error and main_page.status_code == 0:
        return build_metric(
            CATEGORY_NAME, "ssl_enabled", weight,
            value=False, passed=False,
            evidence=f"fetch failed: {main_page.error}",
        )
    is_https = main_page.final_url.startswith("https://")
    return build_metric(
        CATEGORY_NAME, "ssl_enabled", weight,
        value=is_https, passed=is_https,
        evidence=f"final_url={main_page.final_url}",
    )


async def _check_robots_txt(client: httpx.AsyncClient, domain: str) -> MetricResult:
    """robots_txt — 200 + 비어있지 않음 + disallow:/ 전역 차단 ❌."""
    weight = TECHNICAL_METRIC_WEIGHTS["robots_txt"]
    url = f"https://{domain}/robots.txt"
    try:
        resp = await client.get(url)
    except (httpx.HTTPError, OSError) as exc:
        return build_metric(
            CATEGORY_NAME, "robots_txt", weight,
            value=False, passed=False,
            evidence=f"fetch failed: {str(exc)[:200]}",
        )

    text = resp.text or ""
    found = resp.status_code == 200 and bool(text.strip())
    lower = text.lower()
    has_sitemap_ref = found and "sitemap:" in lower
    # `"allow:" not in "disallow:"` 는 substring 매치 → False. v1 의 동일 버그를
    # 재현하지 않도록 줄 시작 ^Allow: 만 정확히 매칭 (Disallow: 와 분리).
    has_standalone_allow = found and bool(
        re.search(r"^\s*allow:", lower, re.MULTILINE)
    )
    disallow_all = found and "disallow: /" in lower and not has_standalone_allow
    passed = found and not disallow_all

    if has_sitemap_ref:
        summary = "found+sitemap_ref"
    elif passed:
        summary = "found"
    elif disallow_all:
        summary = "disallow_all"
    else:
        summary = "missing"

    parts = [f"status={resp.status_code}", f"size={len(text)}b"]
    if has_sitemap_ref:
        parts.append("sitemap_ref")
    if disallow_all:
        parts.append("disallow_all")

    return build_metric(
        CATEGORY_NAME, "robots_txt", weight,
        value=summary, passed=passed,
        evidence=";".join(parts),
    )


async def _check_sitemap(client: httpx.AsyncClient, domain: str) -> MetricResult:
    """sitemap_xml — /sitemap.xml 또는 /sitemap_index.xml 200 + XML 응답."""
    weight = TECHNICAL_METRIC_WEIGHTS["sitemap_xml"]
    candidates = (
        f"https://{domain}/sitemap.xml",
        f"https://{domain}/sitemap_index.xml",
    )
    last_err: str | None = None
    for candidate in candidates:
        try:
            resp = await client.get(candidate)
        except (httpx.HTTPError, OSError) as exc:
            last_err = f"fetch failed: {str(exc)[:200]}"
            continue
        if resp.status_code == 200:
            head = resp.text[:500] if resp.text else ""
            if "<?xml" in head[:100] or "<urlset" in head or "<sitemapindex" in head:
                return build_metric(
                    CATEGORY_NAME, "sitemap_xml", weight,
                    value=candidate, passed=True,
                    evidence=f"status=200;head_len={len(head)}",
                )
    return build_metric(
        CATEGORY_NAME, "sitemap_xml", weight,
        value=None, passed=False,
        evidence=last_err or "neither sitemap.xml nor sitemap_index.xml found",
    )


def _check_canonical(soup: BeautifulSoup | None, fetch_error: str | None) -> MetricResult:
    """canonical_tag — link[rel=canonical] 존재 + href 비어있지 않음."""
    weight = TECHNICAL_METRIC_WEIGHTS["canonical_tag"]
    if soup is None:
        return build_metric(
            CATEGORY_NAME, "canonical_tag", weight,
            value=None, passed=False,
            evidence=f"main page unavailable: {fetch_error or 'no soup'}",
        )
    link = soup.find("link", rel="canonical")
    if link is not None:
        href = (link.get("href") or "").strip()
        if href:
            return build_metric(
                CATEGORY_NAME, "canonical_tag", weight,
                value=href, passed=True,
                evidence="canonical link present",
            )
    return build_metric(
        CATEGORY_NAME, "canonical_tag", weight,
        value=None, passed=False,
        evidence="canonical link not found in main page",
    )


def _check_mobile_viewport(soup: BeautifulSoup | None, fetch_error: str | None) -> MetricResult:
    """mobile_viewport — meta[name=viewport] 존재 + content 에 width= 포함."""
    weight = TECHNICAL_METRIC_WEIGHTS["mobile_viewport"]
    if soup is None:
        return build_metric(
            CATEGORY_NAME, "mobile_viewport", weight,
            value=None, passed=False,
            evidence=f"main page unavailable: {fetch_error or 'no soup'}",
        )
    meta = soup.find("meta", attrs={"name": "viewport"})
    if meta is not None:
        content = (meta.get("content") or "").strip()
        if content:
            has_width = "width=" in content
            return build_metric(
                CATEGORY_NAME, "mobile_viewport", weight,
                value=content, passed=has_width,
                evidence="width=present" if has_width else "width=missing",
            )
    return build_metric(
        CATEGORY_NAME, "mobile_viewport", weight,
        value=None, passed=False,
        evidence="meta[name=viewport] not found",
    )


def _check_page_speed(main_page: MainPage) -> MetricResult:
    """page_speed — main page 응답 시간이 임계값(<2000ms) 미만이면 passed."""
    weight = TECHNICAL_METRIC_WEIGHTS["page_speed"]
    if main_page.error and main_page.status_code == 0:
        return build_metric(
            CATEGORY_NAME, "page_speed", weight,
            value=None, passed=False,
            threshold=PAGE_SPEED_THRESHOLD_MS,
            evidence=f"fetch failed: {main_page.error}",
        )
    elapsed = round(main_page.elapsed_ms, 1)
    passed = elapsed < PAGE_SPEED_THRESHOLD_MS
    return build_metric(
        CATEGORY_NAME, "page_speed", weight,
        value=elapsed, passed=passed,
        threshold=PAGE_SPEED_THRESHOLD_MS,
        evidence=f"elapsed_ms={elapsed};size={main_page.content_size}b",
    )


async def analyze(url: str, options: AnalysisOptions) -> CategoryMetrics:
    """Technical 카테고리 메트릭 분석 (실측, G5 청크).

    카테고리 단위로 ~3회 GET (main / robots.txt / sitemap.xml). 카테고리 모듈은
    독립 fetch — 5축 모두 같은 HTML이 필요한 비효율은 후속 최적화 청크에서 캐시
    도입 (Phase 1 트래픽이 작아 영향 미미).

    Args:
        url: 자사/경쟁사 사이트 URL.
        options: ``AnalysisOptions`` — timeout / user_agent / external_api 플래그.

    Returns:
        ``CategoryMetrics`` — 6 MetricResult + score 0~100.
    """
    domain = _domain_from_url(url)
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
        robots_metric = await _check_robots_txt(client, domain)
        sitemap_metric = await _check_sitemap(client, domain)

    ssl_metric = _check_ssl(main_page)
    canonical_metric = _check_canonical(main_page.soup, main_page.error)
    viewport_metric = _check_mobile_viewport(main_page.soup, main_page.error)
    speed_metric = _check_page_speed(main_page)

    # weights.py 의 키 순서를 따라 metrics 리스트 정렬 — UI 표시 순서 안정.
    metrics = [
        ssl_metric, robots_metric, sitemap_metric,
        canonical_metric, viewport_metric, speed_metric,
    ]
    return build_category_metrics(metrics)
