"""Content 카테고리 — 콘텐츠 길이 / 가독성 / FAQ 존재 / 신선도.

SPEC §7-1: 콘텐츠 길이, 가독성, 키워드 분포, 헤딩 구조, 이미지 alt, 인용 가능성.

Phase 1 G2는 skeleton — 4종 메트릭 모두 stub. G3 이후 v1 구현
(``app.scoring.v1.content``, textstat 사용)을 표준 스키마로 옮겨 채움.
"""
from __future__ import annotations

from app.scoring._common import build_category_metrics, stub_metric
from app.scoring.schemas import AnalysisOptions, CategoryMetrics
from app.scoring.weights import CONTENT_METRIC_WEIGHTS


CATEGORY_NAME = "content"


async def analyze(url: str, options: AnalysisOptions) -> CategoryMetrics:
    """Content 카테고리 메트릭 분석 (skeleton).

    Returns:
        ``CategoryMetrics`` — score 0.0, 4개 stub MetricResult.
    """
    metrics = [
        stub_metric(CATEGORY_NAME, key, weight)
        for key, weight in CONTENT_METRIC_WEIGHTS.items()
    ]
    return build_category_metrics(metrics)
