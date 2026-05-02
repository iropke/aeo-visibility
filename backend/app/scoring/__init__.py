"""5축 카테고리 분석 엔진 (SPEC §7).

공개 API:
- ``CategoryMetrics`` / ``MetricResult`` / ``Improvement`` / ``AnalysisOptions``
  / ``CategoryName`` / ``ALL_CATEGORIES`` (schemas)
- ``ANALYSIS_VERSION`` / ``CATEGORY_WEIGHTS`` / ``METRIC_WEIGHTS``
  / ``compute_overall_score`` (weights)
- ``CATEGORY_MODULES`` — { name → module with ``analyze(url, options)`` }
  (G3 routers/analyses.py + G4 BackgroundTasks가 이 dict 통해 카테고리 호출)

사용 예 (G3 이후):
    from app.scoring import CATEGORY_MODULES, AnalysisOptions, ALL_CATEGORIES
    options = AnalysisOptions()
    results = await asyncio.gather(*[
        CATEGORY_MODULES[cat].analyze(url, options) for cat in ALL_CATEGORIES
    ])
    cat_scores = {cat: r.score for cat, r in zip(ALL_CATEGORIES, results)}
    overall = compute_overall_score(cat_scores)

skeleton 단계: 모든 카테고리가 stub MetricResult를 반환 → 모든 score = 0.0.
실제 분석 로직은 후속 청크에서 채움.
"""
from __future__ import annotations

from app.scoring import (
    authority,
    content,
    structured,
    technical,
    visibility,
)
from app.scoring.schemas import (
    ALL_CATEGORIES,
    AnalysisOptions,
    CategoryMetrics,
    CategoryName,
    Improvement,
    ImprovementEffort,
    ImprovementPriority,
    MetricResult,
    MetricValue,
    compute_score,
)
from app.scoring.weights import (
    ANALYSIS_VERSION,
    AUTHORITY_METRIC_WEIGHTS,
    CATEGORY_WEIGHTS,
    CONTENT_METRIC_WEIGHTS,
    METRIC_WEIGHTS,
    STRUCTURED_METRIC_WEIGHTS,
    TECHNICAL_METRIC_WEIGHTS,
    VISIBILITY_METRIC_WEIGHTS,
    compute_overall_score,
    validate_weights,
)


# 카테고리명 → 분석 모듈 매핑. 각 모듈은 ``analyze(url, options) -> CategoryMetrics``.
CATEGORY_MODULES: dict[CategoryName, object] = {
    "technical":  technical,
    "structured": structured,
    "content":    content,
    "authority":  authority,
    "visibility": visibility,
}


__all__ = [
    # schemas
    "ALL_CATEGORIES",
    "AnalysisOptions",
    "CategoryMetrics",
    "CategoryName",
    "Improvement",
    "ImprovementEffort",
    "ImprovementPriority",
    "MetricResult",
    "MetricValue",
    "compute_score",
    # weights
    "ANALYSIS_VERSION",
    "AUTHORITY_METRIC_WEIGHTS",
    "CATEGORY_WEIGHTS",
    "CONTENT_METRIC_WEIGHTS",
    "METRIC_WEIGHTS",
    "STRUCTURED_METRIC_WEIGHTS",
    "TECHNICAL_METRIC_WEIGHTS",
    "VISIBILITY_METRIC_WEIGHTS",
    "compute_overall_score",
    "validate_weights",
    # registry
    "CATEGORY_MODULES",
]
