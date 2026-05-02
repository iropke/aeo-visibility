"""Technical 카테고리 — SSL / robots.txt / sitemap / canonical / mobile / page speed.

SPEC §7-1: SSL, robots.txt, sitemap, 페이지 속도, mobile-friendly, HTTP 응답.

Phase 1 G2는 skeleton — 모든 메트릭이 stub MetricResult 반환 (passed=False).
G3 이후 v1 구현(``app.scoring.v1.technical``)을 표준 스키마로 옮겨 채움.
"""
from __future__ import annotations

from app.scoring._common import build_category_metrics, stub_metric
from app.scoring.schemas import AnalysisOptions, CategoryMetrics
from app.scoring.weights import TECHNICAL_METRIC_WEIGHTS


CATEGORY_NAME = "technical"


async def analyze(url: str, options: AnalysisOptions) -> CategoryMetrics:
    """Technical 카테고리 메트릭 분석 (skeleton).

    실제 체크는 G3 이후. 현재는 정의된 메트릭 키 6종이 모두 stub MetricResult.

    Args:
        url: 자사/경쟁사 사이트 URL (정규화 전 raw).
        options: ``AnalysisOptions`` — 타임아웃 / UA / 외부 API 허용 플래그.

    Returns:
        ``CategoryMetrics`` — score 0.0 (모든 메트릭 stub passed=False),
        metrics 리스트는 6개 stub MetricResult.
    """
    metrics = [
        stub_metric(CATEGORY_NAME, key, weight)
        for key, weight in TECHNICAL_METRIC_WEIGHTS.items()
    ]
    return build_category_metrics(metrics)
