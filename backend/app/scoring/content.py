"""Content 카테고리 — 콘텐츠 길이 / 가독성 / FAQ 존재 / 신선도.

SPEC §7-1 메트릭 키 4종 (analysis_version v2.0). G5-content 청크에서 v1 측정
로직을 표준 스키마로 옮김. ``textstat`` 사용. main page HTML 1회 fetch.

각 메트릭은 binary ``passed`` + raw ``value``/``evidence`` 보존. v1 의 부분
점수(예: word_count 100/300/500/1000/1500 단계별 점수)는 단일 임계값으로
단순화 + raw 값을 evidence 에 보존.

한계: ``analyze(url, options)`` 시그니처가 main page URL 만 받아 v1 의
multi-page crawl(/about /contact /blog) 보다 정보 적음. FAQ 가 별도 /faq
페이지에 있는 경우 false negative — 후속 최적화 청크에서 multi-page 도입 검토.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx
from bs4 import BeautifulSoup

from app.scoring._common import (
    MainPage,
    build_category_metrics,
    build_metric,
    fetch_main_page,
)
from app.scoring.schemas import AnalysisOptions, CategoryMetrics, MetricResult
from app.scoring.weights import CONTENT_METRIC_WEIGHTS


log = logging.getLogger(__name__)

CATEGORY_NAME = "content"

# content_length binary 임계값 — v1 의 50점 (300+ words) 경계. SEO 본문 최소.
CONTENT_LENGTH_MIN_WORDS: int = 300

# readability binary 임계값 — Flesch-Kincaid Grade.
# v1 매핑: grade ∈ [6,12] = 100, <6 = 70, [12,16] = 60, >16 = 40.
# v1 의 "60점 이상 = fail 아님" 범위를 v2 binary 에 매핑 — [3, 16].
# (grade <3 은 매우 어린이용 텍스트, 일반 콘텐츠에선 거의 발생 ❌.)
READABILITY_MIN_GRADE: float = 3.0
READABILITY_MAX_GRADE: float = 16.0
READABILITY_MIN_WORDS: int = 30  # textstat 측정 최소 텍스트.

# content_freshness binary 임계값 — 1년 이내 수정. v1 의 40점(>365일) 경계.
FRESHNESS_MAX_DAYS: int = 365

# 메타 날짜 우선순위 — 가장 정확한 modified 시점부터.
DATE_META_NAMES: tuple[str, ...] = (
    "article:modified_time",
    "article:published_time",
    "og:updated_time",
    "last-modified",
    "date",
    "DC.date.modified",
)

# FAQ 휴리스틱 — heading 텍스트에 포함되면 FAQ 섹션으로 인정.
FAQ_HEADING_KEYWORDS: tuple[str, ...] = (
    "faq", "frequently asked", "questions", "q&a",
)


def _unavailable(metric_key: str, weight: float, fetch_error: str | None) -> MetricResult:
    """soup=None 일 때 공통 evidence — fetch 실패 메시지 보존."""
    return build_metric(
        CATEGORY_NAME, metric_key, weight,
        value=None, passed=False,
        evidence=f"main page unavailable: {fetch_error or 'no soup'}",
    )


def _extract_visible_text(soup: BeautifulSoup) -> str:
    """script/style/nav/header/footer/aside 제거 후 visible text 추출.

    BeautifulSoup 4의 ``decompose()`` 로 in-place 수정 — 호출자가 같은 soup 을
    다른 메트릭에서 재사용하면 영향. 단, 이 함수는 이 카테고리 안에서만 사용
    되고 호출 후 헤딩/script lookup 은 ``content_length``/``readability`` 외엔
    안 함 → 안전. (FAQ check 는 별도 함수 + raw soup 사용.)
    """
    # 호출자에게 영향 주지 않도록 사본 사용 — bs4 copy 는 lxml 트리 복제 비용.
    # 비용 트레이드오프: 페이지 크기 ~50KB 기준 ms 단위 — 안전성 우선.
    from copy import copy as shallow_copy
    cloned = shallow_copy(soup)
    for tag in cloned(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    text = cloned.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text)


def _check_content_length(
    soup: BeautifulSoup | None, fetch_error: str | None
) -> MetricResult:
    """content_length — visible text word count >= 300."""
    weight = CONTENT_METRIC_WEIGHTS["content_length"]
    if soup is None:
        return _unavailable("content_length", weight, fetch_error)

    text = _extract_visible_text(soup)
    word_count = len(text.split())
    passed = word_count >= CONTENT_LENGTH_MIN_WORDS
    return build_metric(
        CATEGORY_NAME, "content_length", weight,
        value=word_count, passed=passed,
        threshold=float(CONTENT_LENGTH_MIN_WORDS),
        evidence=f"word_count={word_count};threshold={CONTENT_LENGTH_MIN_WORDS}",
    )


def _check_readability(
    soup: BeautifulSoup | None, fetch_error: str | None
) -> MetricResult:
    """readability — Flesch-Kincaid Grade in [6, 16]."""
    weight = CONTENT_METRIC_WEIGHTS["readability"]
    if soup is None:
        return _unavailable("readability", weight, fetch_error)

    text = _extract_visible_text(soup)
    word_count = len(text.split())
    if word_count < READABILITY_MIN_WORDS:
        return build_metric(
            CATEGORY_NAME, "readability", weight,
            value=None, passed=False,
            evidence=f"insufficient text for readability (words={word_count})",
        )

    try:
        import textstat  # 모듈 import 비용 1회 — 패키지 import 캐시.
        fk_grade = float(textstat.flesch_kincaid_grade(text))
        reading_ease = float(textstat.flesch_reading_ease(text))
    except Exception as exc:  # noqa: BLE001
        log.warning("textstat failed: %s", exc)
        return build_metric(
            CATEGORY_NAME, "readability", weight,
            value=None, passed=False,
            evidence=f"textstat error: {str(exc)[:100]}",
        )

    fk_grade = round(fk_grade, 1)
    reading_ease = round(reading_ease, 1)
    passed = READABILITY_MIN_GRADE <= fk_grade <= READABILITY_MAX_GRADE
    return build_metric(
        CATEGORY_NAME, "readability", weight,
        value=fk_grade, passed=passed,
        threshold=READABILITY_MAX_GRADE,
        evidence=(
            f"flesch_kincaid_grade={fk_grade};reading_ease={reading_ease};"
            f"range=[{READABILITY_MIN_GRADE},{READABILITY_MAX_GRADE}]"
        ),
    )


def _check_faq_presence(
    soup: BeautifulSoup | None, fetch_error: str | None
) -> MetricResult:
    """faq_presence — FAQPage schema OR FAQ heading 키워드 OR <details> 요소 존재.

    한계: main page only 검사 — /faq 같은 별도 페이지 FAQ 는 false negative.
    """
    weight = CONTENT_METRIC_WEIGHTS["faq_presence"]
    if soup is None:
        return _unavailable("faq_presence", weight, fetch_error)

    methods: list[str] = []

    # 1) FAQPage schema (JSON-LD).
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (json.JSONDecodeError, AttributeError, TypeError):
            continue
        if isinstance(data, dict) and data.get("@type") == "FAQPage":
            methods.append("faq_schema")
            break
        if isinstance(data, list):
            if any(
                isinstance(item, dict) and item.get("@type") == "FAQPage"
                for item in data
            ):
                methods.append("faq_schema")
                break

    # 2) FAQ heading keywords.
    for heading in soup.find_all(["h1", "h2", "h3", "h4"]):
        h_text = heading.get_text(strip=True).lower()
        if any(kw in h_text for kw in FAQ_HEADING_KEYWORDS):
            methods.append("faq_heading")
            break

    # 3) <details> 요소 (HTML5 disclosure).
    if soup.find("details") is not None:
        methods.append("details_element")

    methods = list(dict.fromkeys(methods))  # dedup, 순서 보존.
    passed = bool(methods)
    return build_metric(
        CATEGORY_NAME, "faq_presence", weight,
        value=",".join(methods) if methods else None,
        passed=passed,
        evidence=("methods=" + ",".join(methods)) if methods else "no FAQ signals (main page only)",
    )


def _parse_freshness_date(content: str) -> datetime | None:
    """ISO 8601 (메타 태그) 또는 RFC 2822 (HTTP Last-Modified) 파싱."""
    s = content.strip()
    if not s:
        return None
    # ISO 8601 — 'Z' 접미사를 +00:00 으로 정규화.
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        pass
    # RFC 2822 (HTTP Last-Modified, 'Wed, 21 Oct 2015 07:28:00 GMT').
    try:
        dt = parsedate_to_datetime(s)
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        pass
    return None


def _check_content_freshness(
    soup: BeautifulSoup | None,
    headers: dict[str, str],
    fetch_error: str | None,
) -> MetricResult:
    """content_freshness — meta 또는 Last-Modified header 의 날짜가 365일 이내."""
    weight = CONTENT_METRIC_WEIGHTS["content_freshness"]
    if soup is None:
        return _unavailable("content_freshness", weight, fetch_error)

    # 1) 메타 태그 우선 (article:modified_time 등).
    for name in DATE_META_NAMES:
        meta = soup.find("meta", property=name) or soup.find(
            "meta", attrs={"name": name}
        )
        content = (meta.get("content") if meta else "") or ""
        if not content.strip():
            continue
        dt = _parse_freshness_date(content)
        if dt is None:
            continue
        days_ago = (datetime.now(timezone.utc) - dt).days
        passed = 0 <= days_ago <= FRESHNESS_MAX_DAYS
        return build_metric(
            CATEGORY_NAME, "content_freshness", weight,
            value=days_ago, passed=passed,
            threshold=float(FRESHNESS_MAX_DAYS),
            evidence=f"source=meta:{name};date={content.strip()[:60]};days_ago={days_ago}",
        )

    # 2) HTTP Last-Modified 헤더 폴백.
    last_modified = headers.get("last-modified", "")
    if last_modified:
        dt = _parse_freshness_date(last_modified)
        if dt is not None:
            days_ago = (datetime.now(timezone.utc) - dt).days
            passed = 0 <= days_ago <= FRESHNESS_MAX_DAYS
            return build_metric(
                CATEGORY_NAME, "content_freshness", weight,
                value=days_ago, passed=passed,
                threshold=float(FRESHNESS_MAX_DAYS),
                evidence=f"source=header;date={last_modified[:60]};days_ago={days_ago}",
            )

    return build_metric(
        CATEGORY_NAME, "content_freshness", weight,
        value=None, passed=False,
        evidence="no parseable modification date in meta or Last-Modified header",
    )


async def analyze(url: str, options: AnalysisOptions) -> CategoryMetrics:
    """Content 카테고리 메트릭 분석 (실측, G5-content 청크).

    main page 1회 fetch → 4 메트릭 모두 같은 soup 으로 측정. fetch 실패 시
    4 메트릭 모두 ``unavailable`` evidence + passed=False.
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
        main_page: MainPage = await fetch_main_page(client, url)

    soup = main_page.soup
    err = main_page.error

    metrics = [
        _check_content_length(soup, err),
        _check_readability(soup, err),
        _check_faq_presence(soup, err),
        _check_content_freshness(soup, main_page.headers, err),
    ]
    return build_category_metrics(metrics)
