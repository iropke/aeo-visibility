"""Authority 카테고리 — 도메인 나이 / 소셜 링크 / 연락처 / 보안 헤더.

SPEC §7-1: 도메인 신뢰도, whois 정보, 백링크 추정, HTTPS 평가, E-E-A-T 신호.

Phase 1 G2는 skeleton — 4종 메트릭 모두 stub. G3 이후 v1 구현
(``app.scoring.v1.authority``, python-whois 사용)을 표준 스키마로 옮겨 채움.
무거운 외부 호출(WHOIS)은 ``options.enable_external_apis`` 플래그로 제어 예정.
"""
from __future__ import annotations

from app.scoring._common import build_category_metrics, stub_metric
from app.scoring.schemas import AnalysisOptions, CategoryMetrics
from app.scoring.weights import AUTHORITY_METRIC_WEIGHTS


CATEGORY_NAME = "authority"


async def analyze(url: str, options: AnalysisOptions) -> CategoryMetrics:
    """Authority 카테고리 메트릭 분석 (skeleton).

    Returns:
        ``CategoryMetrics`` — score 0.0, 4개 stub MetricResult.
    """
    metrics = [
        stub_metric(CATEGORY_NAME, key, weight)
        for key, weight in AUTHORITY_METRIC_WEIGHTS.items()
    ]
    return build_category_metrics(metrics)
