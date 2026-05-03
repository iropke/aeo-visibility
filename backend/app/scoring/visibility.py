"""Visibility 카테고리 — LLM 인용 가능성 / brand·domain 매치.

SPEC §7-1 메트릭 키 3종 (analysis_version v2.0). G5-visibility 청크에서 v1
(``app.scoring.v1.visibility``) 의 Claude 호출 시퀀스를 표준 스키마로 옮김.

- ``llm_brand_mention`` (0.50): N query 중 brand(domain prefix) 매치 ≥1
- ``llm_domain_mention`` (0.30): N query 중 domain 전체 매치 ≥1
- ``queries_tested`` (0.20): query 개수 ≥ ``QUERIES_TARGET_COUNT`` (sanity)

SPEC §7-3 #4 예외: visibility 메트릭은 LLM 응답 자체에서 도출되므로 카테고리
내부에서 LLM 호출 (``options.enable_llm_visibility=True`` 일 때만). 기본 OFF
일 때는 3 메트릭 모두 stub (passed=False, evidence="llm_visibility disabled").

Phase 1 구현 범위 (reboot-service-concept §1-4):
- ``visibility_engines`` 의 'claude' 만 실제 호출. 다른 키는 receive 시 warning +
  skip (Phase 2 multi-engine 에서 add-on 엔진 호출 추가).
- ``visibility_user_queries`` 비어있으면 자동 5 query 생성 (v1 _generate_queries
  패턴). 비어있지 않으면 사용자 입력 그대로 — Phase 2/3 카테고리/상품명 UX.
- ``visibility_compare_brands`` 는 Phase 1 무시 (Phase 3 경쟁사 비교 시 활용).

mock 가능 구조: ``anthropic`` 모듈을 module-level import → 테스트가
``visibility_mod.anthropic.AsyncAnthropic = MagicMock(...)`` 로 교체 가능.
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

import anthropic
import httpx

from app.config import get_settings
from app.scoring._common import (
    MainPage,
    build_category_metrics,
    build_metric,
    fetch_main_page,
)
from app.scoring.schemas import AnalysisOptions, CategoryMetrics, MetricResult
from app.scoring.weights import VISIBILITY_METRIC_WEIGHTS


log = logging.getLogger(__name__)

CATEGORY_NAME = "visibility"

# Phase 1 실제 호출 엔진 — 1종. Phase 2 multi-engine 에서 확장.
PHASE1_SUPPORTED_ENGINES: frozenset[str] = frozenset({"claude"})

# query 자동 생성 목표 개수 (v1 동일). queries_tested sanity 임계값.
QUERIES_TARGET_COUNT: int = 5

# fallback 시 최소 query 개수 (LLM 호출 실패 시).
QUERIES_FALLBACK_COUNT: int = 3

# brand 매치를 위한 최소 토큰 길이 — 너무 짧으면 false positive 위험 (v1 동일).
BRAND_MIN_LENGTH: int = 4

# Claude 모델 — v1 동일. 비용 고려 Haiku 유지.
CLAUDE_MODEL: str = "claude-haiku-4-5-20251001"
CLAUDE_QUERY_GEN_MAX_TOKENS: int = 300
CLAUDE_VISIBILITY_CHECK_MAX_TOKENS: int = 500


def _stub_metric(metric_key: str, weight: float, reason: str) -> MetricResult:
    """enable_llm_visibility=False 또는 LLM 사용 불가 시 공통 stub."""
    return build_metric(
        CATEGORY_NAME, metric_key, weight,
        value=None, passed=False,
        evidence=f"llm_visibility disabled: {reason}",
    )


def _all_stub(reason: str) -> CategoryMetrics:
    """3 메트릭 모두 stub — analyze() 의 모든 short-circuit 분기 공통."""
    metrics = [
        _stub_metric(key, weight, reason)
        for key, weight in VISIBILITY_METRIC_WEIGHTS.items()
    ]
    return build_category_metrics(metrics)


def _domain_from_url(url: str) -> str:
    """URL → 도메인 (www. 제거, lower-case). 매치 비교 단일 소스."""
    parsed = urlparse(url)
    host = (parsed.netloc or parsed.path or "").lower().strip("/")
    return host[4:] if host.startswith("www.") else host


def _brand_token(domain: str) -> str:
    """도메인에서 brand 토큰 추출 — 첫 라벨 (e.g. 'example' from 'example.com')."""
    return domain.split(".")[0] if domain else ""


def _extract_site_topic(main_page: MainPage, fallback_domain: str) -> str:
    """title / meta description / h1 결합 → query 생성용 site topic.

    fetch 실패 시 도메인만 반환. v1 _extract_site_topic 와 동일 로직.
    """
    if main_page.soup is None:
        return fallback_domain

    parts: list[str] = []
    title = main_page.soup.find("title")
    if title:
        t = title.get_text(strip=True)
        if t:
            parts.append(t)

    meta = main_page.soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        parts.append(meta["content"].strip())

    h1 = main_page.soup.find("h1")
    if h1:
        h = h1.get_text(strip=True)
        if h:
            parts.append(h)

    return " | ".join(parts) if parts else fallback_domain


def _fallback_queries(domain: str) -> list[str]:
    """LLM 호출 실패 시 hardcoded fallback (v1 동일, 3개)."""
    return [
        f"What is {domain}?",
        f"Best services by {domain}",
        f"Tell me about {domain} company",
    ]


async def _generate_queries(
    client: "anthropic.AsyncAnthropic",
    site_topic: str,
    domain: str,
) -> tuple[list[str], str]:
    """LLM 으로 5 query 생성. 실패 시 fallback 3 query.

    Returns:
        (queries, source) — source ∈ {'llm', 'fallback'}.
    """
    try:
        message = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_QUERY_GEN_MAX_TOKENS,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Given this website topic/description: '{site_topic}' "
                        f"(domain: {domain}), generate exactly {QUERIES_TARGET_COUNT} "
                        f"search queries that a user might ask an AI assistant that "
                        f"could lead to this website being mentioned. Return only the "
                        f"queries, one per line, no numbering."
                    ),
                }
            ],
        )
        text = message.content[0].text.strip()
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            log.warning("LLM returned empty query list, using fallback")
            return _fallback_queries(domain), "fallback"
        return lines[:QUERIES_TARGET_COUNT], "llm"
    except Exception as exc:  # noqa: BLE001
        log.warning("Query generation failed (%s), using fallback", exc)
        return _fallback_queries(domain), "fallback"


async def _check_query_visibility(
    client: "anthropic.AsyncAnthropic",
    query: str,
    domain: str,
    brand: str,
) -> dict:
    """단일 query 에 Claude 호출 → brand/domain 매치 검사.

    Returns dict with keys: query / domain_match / brand_match / error?
    """
    try:
        message = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_VISIBILITY_CHECK_MAX_TOKENS,
            messages=[{"role": "user", "content": query}],
        )
        response_text = message.content[0].text.lower()
        domain_match = bool(domain) and domain in response_text
        brand_match = (
            len(brand) >= BRAND_MIN_LENGTH and brand in response_text
        )
        return {
            "query": query,
            "domain_match": domain_match,
            "brand_match": brand_match,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "query": query,
            "domain_match": False,
            "brand_match": False,
            "error": str(exc)[:100],
        }


def _format_query_evidence(results: list[dict], match_key: str) -> str:
    """raw query 결과를 evidence 문자열로 — UI 디버그 + reproducibility."""
    matches = sum(1 for r in results if r.get(match_key))
    sample = ";".join(
        f"q={r['query'][:40]}|m={'1' if r.get(match_key) else '0'}"
        for r in results[:QUERIES_TARGET_COUNT]
    )
    return f"matches={matches}/{len(results)};{sample}"


async def analyze(url: str, options: AnalysisOptions) -> CategoryMetrics:
    """Visibility 카테고리 메트릭 분석 (실측, G5-visibility 청크).

    Phase 1: Claude 단일 엔진. ``enable_llm_visibility=False`` (기본) 또는
    'claude' 가 ``visibility_engines`` 에 없으면 3 메트릭 모두 stub.

    절차:
    1. enable_llm_visibility=False → all_stub
    2. 'claude' not in visibility_engines → all_stub (다른 엔진 호출은 Phase 2)
    3. claude_api_key 미설정 → all_stub (LLM 호출 불가)
    4. main page fetch → site_topic 추출
    5. visibility_user_queries 비면 자동 5 query 생성, 아니면 그대로 사용
    6. 각 query 에 Claude 호출 → brand/domain 매치 집계
    7. 3 메트릭 산출 (brand_mention / domain_mention / queries_tested)
    """
    weights = VISIBILITY_METRIC_WEIGHTS

    # 1) LLM 호출 비활성화.
    if not options.enable_llm_visibility:
        return _all_stub("enable_llm_visibility=False")

    # 2) 엔진 선택 검증 — Phase 1 은 claude 만.
    requested = set(options.visibility_engines)
    unsupported = requested - PHASE1_SUPPORTED_ENGINES
    if unsupported:
        log.warning(
            "Phase 1 only supports 'claude'; ignoring engines: %s",
            sorted(unsupported),
        )
    if "claude" not in requested:
        return _all_stub(
            f"no supported engine in visibility_engines={sorted(requested)}"
        )

    # 3) API key 확인.
    settings = get_settings()
    api_key = getattr(settings, "claude_api_key", None)
    if not api_key:
        return _all_stub("claude_api_key not configured")

    # 4) main page fetch — site_topic 추출용.
    domain = _domain_from_url(url)
    brand = _brand_token(domain)
    headers = {
        "User-Agent": options.user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    timeout = httpx.Timeout(options.timeout_seconds)
    async with httpx.AsyncClient(
        headers=headers, follow_redirects=True, timeout=timeout, verify=True,
    ) as http_client:
        main_page = await fetch_main_page(http_client, url)
    site_topic = _extract_site_topic(main_page, fallback_domain=domain)

    # 5) query 결정 — 사용자 입력 우선, 없으면 자동 생성.
    llm_client = anthropic.AsyncAnthropic(api_key=api_key)
    if options.visibility_user_queries:
        queries = list(options.visibility_user_queries)[:QUERIES_TARGET_COUNT]
        query_source = "user"
    else:
        queries, query_source = await _generate_queries(
            llm_client, site_topic, domain
        )

    # 6) 각 query Claude 호출 → 매치 집계.
    results: list[dict] = []
    for q in queries:
        result = await _check_query_visibility(llm_client, q, domain, brand)
        results.append(result)

    brand_matches = sum(1 for r in results if r.get("brand_match"))
    domain_matches = sum(1 for r in results if r.get("domain_match"))
    queries_count = len(queries)

    # 7) 3 메트릭 산출.
    brand_evidence = _format_query_evidence(results, "brand_match")
    domain_evidence = _format_query_evidence(results, "domain_match")

    metrics = [
        build_metric(
            CATEGORY_NAME, "llm_brand_mention", weights["llm_brand_mention"],
            value=brand_matches, passed=brand_matches >= 1,
            threshold=1.0,
            evidence=f"engine=claude;source={query_source};{brand_evidence}",
        ),
        build_metric(
            CATEGORY_NAME, "llm_domain_mention", weights["llm_domain_mention"],
            value=domain_matches, passed=domain_matches >= 1,
            threshold=1.0,
            evidence=f"engine=claude;source={query_source};{domain_evidence}",
        ),
        build_metric(
            CATEGORY_NAME, "queries_tested", weights["queries_tested"],
            value=queries_count, passed=queries_count >= QUERIES_TARGET_COUNT,
            threshold=float(QUERIES_TARGET_COUNT),
            evidence=(
                f"engine=claude;source={query_source};count={queries_count};"
                f"target={QUERIES_TARGET_COUNT}"
            ),
        ),
    ]
    return build_category_metrics(metrics)
