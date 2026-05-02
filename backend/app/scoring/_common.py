"""5축 카테고리 모듈이 공통으로 쓰는 skeleton 헬퍼.

Phase 1 G2는 skeleton — 실제 HTTP / 외부 API 호출은 G3 이후 채움. 이 파일은
"메트릭 키 정의 → MetricResult 리스트 → CategoryMetrics" 변환 패턴을 캡슐화.

각 카테고리 모듈이 직접 ``MetricResult(...)`` 를 생성해도 되지만, 일관성을 위해
``stub_metric()`` / ``build_category_metrics()`` 사용을 권장.
"""
from __future__ import annotations

from app.scoring.schemas import (
    CategoryMetrics,
    MetricResult,
    MetricValue,
    compute_score,
)


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
