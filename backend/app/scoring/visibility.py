"""Visibility 카테고리 — LLM 인용 가능성 / 검색 노출 추정.

SPEC §7-1: LLM 인용 가능성 (Claude API에 query → 답변에 사이트 등장 여부).

Phase 1 G2는 skeleton — 3종 메트릭 모두 stub. G3 이후 v1 구현
(``app.scoring.v1.visibility``, anthropic SDK 사용)을 표준 스키마로 옮겨 채움.
LLM 호출은 ``options.enable_llm_visibility`` 플래그로 제어. SPEC §7-3 #4 원칙
("LLM 호출은 카테고리 내부에서 ❌, 통합 호출")과의 정합은 G3 설계 시 재검토:
visibility 메트릭이 LLM 응답 자체에서 도출되므로 통합 호출 분리가 어려울 수 있음.
"""
from __future__ import annotations

from app.scoring._common import build_category_metrics, stub_metric
from app.scoring.schemas import AnalysisOptions, CategoryMetrics
from app.scoring.weights import VISIBILITY_METRIC_WEIGHTS


CATEGORY_NAME = "visibility"


async def analyze(url: str, options: AnalysisOptions) -> CategoryMetrics:
    """Visibility 카테고리 메트릭 분석 (skeleton).

    Returns:
        ``CategoryMetrics`` — score 0.0, 3개 stub MetricResult.
    """
    metrics = [
        stub_metric(CATEGORY_NAME, key, weight)
        for key, weight in VISIBILITY_METRIC_WEIGHTS.items()
    ]
    return build_category_metrics(metrics)
