"""분석 엔진 가중치 + 메트릭 키 레지스트리.

가중치는 모듈 외부 설정 (SPEC §7-3 재작성 원칙 #3). 각 카테고리의 메트릭 키는
이 파일이 단일 소스 — 카테고리 모듈은 ``METRIC_WEIGHTS[category_name]`` 를
import해서 사용.

규칙:
1. ``CATEGORY_WEIGHTS`` 합계 = 1.0 (overall_score 계산용).
2. ``METRIC_WEIGHTS[category]`` 의 값(weight) 합계 = 1.0 (카테고리 내 점수 0~100).
3. 키는 안정 식별자 — 변경 ❌, 추가만. (이미 저장된 결과의 raw_metrics 키와
   호환을 깨면 시계열/UI 모두 깨짐)

ANALYSIS_VERSION 은 스키마/가중치/키 셋이 의미있게 바뀔 때 증가. 신규 결과의
``analysis_results.analysis_version`` 컬럼에 기록.
"""
from __future__ import annotations

from app.scoring.schemas import CategoryName


ANALYSIS_VERSION: str = "v2.0"


# ─── 카테고리 가중치 (overall_score 가중평균) ───
# 합계 = 1.0. 5축 균등 가중을 시작점으로, 추후 사용자 데이터로 튜닝.
CATEGORY_WEIGHTS: dict[CategoryName, float] = {
    "technical":  0.20,
    "structured": 0.20,
    "content":    0.20,
    "authority":  0.20,
    "visibility": 0.20,
}


# ─── 카테고리별 메트릭 가중치 (카테고리 내 합계 = 1.0) ───
# 각 키는 안정 식별자. 카테고리 모듈의 ``analyze()`` 가 동일 키로 MetricResult 생성.

TECHNICAL_METRIC_WEIGHTS: dict[str, float] = {
    "ssl_enabled":      0.20,
    "robots_txt":       0.15,
    "sitemap_xml":      0.15,
    "canonical_tag":    0.10,
    "mobile_viewport":  0.15,
    "page_speed":       0.25,
}

STRUCTURED_METRIC_WEIGHTS: dict[str, float] = {
    "json_ld_present":     0.30,
    "open_graph_complete": 0.20,
    "meta_description":    0.20,
    "heading_hierarchy":   0.20,
    "twitter_card":        0.10,
}

CONTENT_METRIC_WEIGHTS: dict[str, float] = {
    "content_length":     0.30,
    "readability":        0.25,
    "faq_presence":       0.20,
    "content_freshness":  0.25,
}

AUTHORITY_METRIC_WEIGHTS: dict[str, float] = {
    "domain_age":          0.30,
    "social_links":        0.25,
    "contact_info":        0.20,
    "security_headers":    0.25,
}

VISIBILITY_METRIC_WEIGHTS: dict[str, float] = {
    "llm_brand_mention":   0.50,
    "llm_domain_mention":  0.30,
    "queries_tested":      0.20,
}


# 카테고리명 → 메트릭 weights dict 매핑 (orchestrator/검증용).
METRIC_WEIGHTS: dict[CategoryName, dict[str, float]] = {
    "technical":  TECHNICAL_METRIC_WEIGHTS,
    "structured": STRUCTURED_METRIC_WEIGHTS,
    "content":    CONTENT_METRIC_WEIGHTS,
    "authority":  AUTHORITY_METRIC_WEIGHTS,
    "visibility": VISIBILITY_METRIC_WEIGHTS,
}


def validate_weights() -> None:
    """모든 가중치 합계가 1.0 ± 1e-3 인지 검증. 실패 시 ValueError.

    모듈 import 시점에 호출되어 가중치 오타를 즉시 검출.
    """
    cat_total = sum(CATEGORY_WEIGHTS.values())
    if abs(cat_total - 1.0) > 1e-3:
        raise ValueError(
            f"CATEGORY_WEIGHTS sum must be 1.0, got {cat_total:.4f}"
        )

    if set(CATEGORY_WEIGHTS.keys()) != set(METRIC_WEIGHTS.keys()):
        raise ValueError(
            "CATEGORY_WEIGHTS keys must match METRIC_WEIGHTS keys"
        )

    for cat, weights in METRIC_WEIGHTS.items():
        m_total = sum(weights.values())
        if abs(m_total - 1.0) > 1e-3:
            raise ValueError(
                f"METRIC_WEIGHTS[{cat!r}] sum must be 1.0, got {m_total:.4f}"
            )
        if not weights:
            raise ValueError(f"METRIC_WEIGHTS[{cat!r}] must have at least one metric")


# import 시 즉시 검증 — 가중치 오타로 인한 점수 스케일 어긋남을 빌드 타임에 차단.
validate_weights()


def compute_overall_score(category_scores: dict[CategoryName, float]) -> float:
    """카테고리 점수 dict에서 전체 가중평균 점수 계산 (0~100).

    부분 분석(Custom Re-analyze, SPEC §7-5)일 경우 일부 카테고리만 dict에 들어옴
    → 해당 카테고리들의 가중치 합으로 정규화하여 0~100 스케일 유지.
    """
    if not category_scores:
        return 0.0
    weights = {
        cat: CATEGORY_WEIGHTS[cat] for cat in category_scores.keys()
    }
    weight_sum = sum(weights.values())
    if weight_sum == 0:
        return 0.0
    score = sum(
        category_scores[cat] * (weights[cat] / weight_sum)
        for cat in category_scores
    )
    return round(score, 2)
