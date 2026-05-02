"""Structured 카테고리 — JSON-LD / OpenGraph / meta description / heading / Twitter.

SPEC §7-1: JSON-LD, schema.org, OpenGraph, Twitter Card, hreflang, canonical.

Phase 1 G2는 skeleton — 5종 메트릭 모두 stub. G3 이후 v1 구현
(``app.scoring.v1.structured``)을 표준 스키마로 옮겨 채움.
"""
from __future__ import annotations

from app.scoring._common import build_category_metrics, stub_metric
from app.scoring.schemas import AnalysisOptions, CategoryMetrics
from app.scoring.weights import STRUCTURED_METRIC_WEIGHTS


CATEGORY_NAME = "structured"


async def analyze(url: str, options: AnalysisOptions) -> CategoryMetrics:
    """Structured 카테고리 메트릭 분석 (skeleton).

    Returns:
        ``CategoryMetrics`` — score 0.0, 5개 stub MetricResult.
    """
    metrics = [
        stub_metric(CATEGORY_NAME, key, weight)
        for key, weight in STRUCTURED_METRIC_WEIGHTS.items()
    ]
    return build_category_metrics(metrics)
