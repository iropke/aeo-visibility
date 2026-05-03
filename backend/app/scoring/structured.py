"""Structured 카테고리 — JSON-LD / OpenGraph / meta description / heading / Twitter.

SPEC §7-1 메트릭 키 5종 (analysis_version v2.0). G5-structured 청크에서 v1 측정
로직(``app.scoring.v1.structured``)을 표준 스키마로 옮김.

각 메트릭은 binary ``passed`` + raw ``value``/``evidence`` 보존. v1 의 부분
점수(예: meta_description 길이별 25/50/75/100 점)는 단일 임계값으로 단순화 +
raw 값(길이/개수/태그 목록)을 evidence 에 보존.

main page HTML 1회 fetch 만 — 외부 API ❌, LLM 호출 ❌.
"""
from __future__ import annotations

import json
import logging

import httpx
from bs4 import BeautifulSoup

from app.scoring._common import (
    MainPage,
    build_category_metrics,
    build_metric,
    fetch_main_page,
)
from app.scoring.schemas import AnalysisOptions, CategoryMetrics, MetricResult
from app.scoring.weights import STRUCTURED_METRIC_WEIGHTS


log = logging.getLogger(__name__)

CATEGORY_NAME = "structured"

# meta description 길이 임계값 — v1 의 50점 이상 경계 (50~200자) 사용.
META_DESC_MIN_LEN: int = 50
META_DESC_MAX_LEN: int = 200

# 필수 OpenGraph 태그 — 4종 모두 존재 + content 비어있지 않으면 passed.
REQUIRED_OG_TAGS: tuple[str, ...] = (
    "og:title", "og:description", "og:image", "og:url",
)


def _unavailable(metric_key: str, weight: float, fetch_error: str | None) -> MetricResult:
    """soup=None 일 때 공통 evidence — fetch 실패 메시지 보존."""
    return build_metric(
        CATEGORY_NAME, metric_key, weight,
        value=None, passed=False,
        evidence=f"main page unavailable: {fetch_error or 'no soup'}",
    )


def _extract_jsonld_types(soup: BeautifulSoup) -> list[str]:
    """``<script type="application/ld+json">`` 안의 @type 들 수집."""
    types: list[str] = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, AttributeError, TypeError):
            continue
        if isinstance(data, dict):
            t = data.get("@type", "")
            if t:
                types.append(str(t))
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    t = item.get("@type", "")
                    if t:
                        types.append(str(t))
    return types


def _check_json_ld(soup: BeautifulSoup | None, fetch_error: str | None) -> MetricResult:
    """json_ld_present — ld+json 스크립트 1개 이상 + @type 추출 가능."""
    weight = STRUCTURED_METRIC_WEIGHTS["json_ld_present"]
    if soup is None:
        return _unavailable("json_ld_present", weight, fetch_error)

    types = _extract_jsonld_types(soup)
    if not types:
        return build_metric(
            CATEGORY_NAME, "json_ld_present", weight,
            value=0, passed=False,
            evidence="no application/ld+json with @type found",
        )
    return build_metric(
        CATEGORY_NAME, "json_ld_present", weight,
        value=len(types), passed=True,
        evidence=f"types={','.join(types[:5])}{'...' if len(types) > 5 else ''}",
    )


def _check_open_graph(soup: BeautifulSoup | None, fetch_error: str | None) -> MetricResult:
    """open_graph_complete — 필수 4종(og:title/description/image/url) 모두 존재."""
    weight = STRUCTURED_METRIC_WEIGHTS["open_graph_complete"]
    if soup is None:
        return _unavailable("open_graph_complete", weight, fetch_error)

    found: list[str] = []
    missing: list[str] = []
    for tag in REQUIRED_OG_TAGS:
        meta = soup.find("meta", property=tag)
        content = (meta.get("content") if meta else "") or ""
        if content.strip():
            found.append(tag)
        else:
            missing.append(tag)

    passed = len(missing) == 0
    if passed:
        evidence = f"all 4 og tags present: {','.join(found)}"
        value: str | int = len(found)
    else:
        evidence = f"missing: {','.join(missing)}"
        value = len(found)

    return build_metric(
        CATEGORY_NAME, "open_graph_complete", weight,
        value=value, passed=passed,
        threshold=float(len(REQUIRED_OG_TAGS)),
        evidence=evidence,
    )


def _check_meta_description(soup: BeautifulSoup | None, fetch_error: str | None) -> MetricResult:
    """meta_description — name=description 메타 + content 길이 50~200."""
    weight = STRUCTURED_METRIC_WEIGHTS["meta_description"]
    if soup is None:
        return _unavailable("meta_description", weight, fetch_error)

    meta = soup.find("meta", attrs={"name": "description"})
    content = (meta.get("content") if meta else "") or ""
    desc = content.strip()
    if not desc:
        return build_metric(
            CATEGORY_NAME, "meta_description", weight,
            value=0, passed=False,
            evidence="meta[name=description] not found or empty",
        )

    length = len(desc)
    passed = META_DESC_MIN_LEN <= length <= META_DESC_MAX_LEN
    return build_metric(
        CATEGORY_NAME, "meta_description", weight,
        value=length, passed=passed,
        threshold=float(META_DESC_MIN_LEN),
        evidence=(
            f"length={length};range=[{META_DESC_MIN_LEN},{META_DESC_MAX_LEN}];"
            f"preview={desc[:60].replace(chr(10), ' ')}"
        ),
    )


def _check_heading_hierarchy(soup: BeautifulSoup | None, fetch_error: str | None) -> MetricResult:
    """heading_hierarchy — H1 정확히 1개 + 레벨 스킵 ❌ (h3 있으면 h2 있어야)."""
    weight = STRUCTURED_METRIC_WEIGHTS["heading_hierarchy"]
    if soup is None:
        return _unavailable("heading_hierarchy", weight, fetch_error)

    counts: dict[str, int] = {}
    for level in range(1, 7):
        tag = f"h{level}"
        n = len(soup.find_all(tag))
        if n:
            counts[tag] = n

    if not counts:
        return build_metric(
            CATEGORY_NAME, "heading_hierarchy", weight,
            value=0, passed=False,
            evidence="no headings found",
        )

    issues: list[str] = []
    h1_count = counts.get("h1", 0)
    if h1_count == 0:
        issues.append("missing h1")
    elif h1_count > 1:
        issues.append(f"multiple h1 ({h1_count})")
    for level in range(3, 7):
        tag = f"h{level}"
        parent = f"h{level - 1}"
        if tag in counts and parent not in counts:
            issues.append(f"{tag} without {parent}")

    passed = h1_count == 1 and not issues
    summary = ",".join(f"{k}={v}" for k, v in counts.items())
    return build_metric(
        CATEGORY_NAME, "heading_hierarchy", weight,
        value=summary, passed=passed,
        evidence=("ok" if passed else "issues: " + "; ".join(issues)),
    )


def _check_twitter_card(soup: BeautifulSoup | None, fetch_error: str | None) -> MetricResult:
    """twitter_card — meta[name=twitter:card] + content 비어있지 않음."""
    weight = STRUCTURED_METRIC_WEIGHTS["twitter_card"]
    if soup is None:
        return _unavailable("twitter_card", weight, fetch_error)

    card = soup.find("meta", attrs={"name": "twitter:card"})
    content = (card.get("content") if card else "") or ""
    card_type = content.strip()
    if not card_type:
        return build_metric(
            CATEGORY_NAME, "twitter_card", weight,
            value=None, passed=False,
            evidence="meta[name=twitter:card] not found",
        )
    return build_metric(
        CATEGORY_NAME, "twitter_card", weight,
        value=card_type, passed=True,
        evidence=f"card={card_type}",
    )


async def analyze(url: str, options: AnalysisOptions) -> CategoryMetrics:
    """Structured 카테고리 메트릭 분석 (실측, G5-structured 청크).

    main page 1회 fetch → 5 메트릭 모두 같은 soup 으로 측정. fetch 실패 시
    5 메트릭 모두 ``unavailable`` evidence + passed=False.

    Args:
        url: 자사/경쟁사 사이트 URL.
        options: ``AnalysisOptions`` — timeout / user_agent.

    Returns:
        ``CategoryMetrics`` — 5 MetricResult + score 0~100.
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
        _check_json_ld(soup, err),
        _check_open_graph(soup, err),
        _check_meta_description(soup, err),
        _check_heading_hierarchy(soup, err),
        _check_twitter_card(soup, err),
    ]
    return build_category_metrics(metrics)
