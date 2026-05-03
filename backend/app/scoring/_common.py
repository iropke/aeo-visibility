"""5축 카테고리 모듈이 공통으로 쓰는 헬퍼.

크게 두 부류:
1. 메트릭 빌더 (``stub_metric`` / ``build_metric`` / ``build_category_metrics``) —
   "메트릭 키 정의 → MetricResult 리스트 → CategoryMetrics" 변환 패턴.
2. main page fetch (``MainPage`` / ``fetch_main_page``) — 5축 중 technical /
   structured / content / authority 가 모두 같은 메인 HTML 을 본다. 카테고리
   모듈이 자체 fetch 해도 되지만 redundant 정의 4중복을 피하기 위해 공통화.

각 카테고리 모듈이 직접 ``MetricResult(...)`` 를 생성해도 되지만, 일관성을 위해
빌더 헬퍼 사용을 권장.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from app.scoring.schemas import (
    CategoryMetrics,
    MetricResult,
    MetricValue,
    compute_score,
)


log = logging.getLogger(__name__)


# i18n 사전 키는 ``scoring.{category}.{metric_key}.{display|description}`` 규칙.
# 프론트엔드는 ``next-intl`` 등으로 동일 키를 lookup.

def _key(category: str, metric_key: str, suffix: str) -> str:
    return f"scoring.{category}.{metric_key}.{suffix}"


def stub_metric(
    category: str,
    metric_key: str,
    weight: float,
    *,
    note: str | None = None,
) -> MetricResult:
    """skeleton MetricResult — passed=False, value=None, evidence는 stub 표시.

    G3 이후 실제 분석 로직이 채워지면 이 호출을 ``passed_metric`` /
    ``failed_metric`` / 직접 ``MetricResult(...)`` 로 교체.
    """
    return MetricResult(
        key=metric_key,
        display_name_key=_key(category, metric_key, "display"),
        description_key=_key(category, metric_key, "description"),
        value=None,
        weight=weight,
        passed=False,
        threshold=None,
        evidence=note or "stub - implementation pending in later chunk",
    )


def build_metric(
    category: str,
    metric_key: str,
    weight: float,
    value: MetricValue,
    passed: bool,
    *,
    threshold: float | None = None,
    evidence: str | None = None,
) -> MetricResult:
    """실제 측정값 기반 MetricResult — G3 이후 카테고리 모듈이 사용.

    ``key`` / ``display_name_key`` / ``description_key`` 의 i18n 규칙을
    한 곳에서 강제.
    """
    return MetricResult(
        key=metric_key,
        display_name_key=_key(category, metric_key, "display"),
        description_key=_key(category, metric_key, "description"),
        value=value,
        weight=weight,
        passed=passed,
        threshold=threshold,
        evidence=evidence,
    )


def build_category_metrics(metrics: list[MetricResult]) -> CategoryMetrics:
    """``MetricResult`` 리스트를 ``CategoryMetrics`` 로 변환 — score 자동 계산.

    weight 합계 검증은 ``CategoryMetrics`` validator + ``compute_score`` 양쪽에서.
    """
    score = compute_score(metrics)
    return CategoryMetrics(score=score, metrics=metrics)


# ─── main page fetch (technical / structured / content / authority 공통) ───

@dataclass(frozen=True)
class MainPage:
    """메인 페이지 fetch 결과 — 카테고리 모듈이 status / soup / final_url / error 사용."""
    status_code: int
    elapsed_ms: float
    content_size: int
    final_url: str
    soup: BeautifulSoup | None
    error: str | None


async def fetch_main_page(client: httpx.AsyncClient, url: str) -> MainPage:
    """메인 페이지 GET — 실패 시 ``MainPage(error=...)`` 반환, 예외 raise ❌.

    httpx 0.28 호환:
    - ``Response.elapsed`` 는 MockTransport 등 일부 경로에서 자동 셋 ❌ →
      ``time.perf_counter()`` 직접 측정 (실 fetch 와 mock 양쪽 동일).
    - ``Response.text`` / ``.content`` / ``.elapsed`` 는 응답 read 후만 안전 →
      ``.content`` 명시 접근으로 read 트리거 고정 (client.get() 기본 read=True 라도).
    """
    start = time.perf_counter()
    try:
        resp = await client.get(url)
        content_bytes = resp.content
        text = resp.text if resp.status_code < 400 else ""
    except (httpx.HTTPError, OSError) as exc:
        return MainPage(
            status_code=0, elapsed_ms=0.0, content_size=0,
            final_url=url, soup=None, error=str(exc)[:200],
        )

    elapsed_ms = (time.perf_counter() - start) * 1000
    soup: BeautifulSoup | None = None
    if resp.status_code < 400 and text:
        try:
            soup = BeautifulSoup(text, "lxml")
        except Exception as exc:  # noqa: BLE001
            log.warning("HTML parse failed for %s: %s", url, exc)

    return MainPage(
        status_code=resp.status_code,
        elapsed_ms=elapsed_ms,
        content_size=len(content_bytes),
        final_url=str(resp.url),
        soup=soup,
        error=None if resp.status_code < 400 else f"HTTP {resp.status_code}",
    )
