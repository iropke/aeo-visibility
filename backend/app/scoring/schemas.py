"""분석 엔진 표준 결과 스키마 (SPEC §7-2 정합).

5축 카테고리(technical/structured/content/authority/visibility)가 공통으로
사용하는 ``MetricResult`` / ``CategoryMetrics`` / ``Improvement`` Pydantic 모델.

DB ``analysis_results.raw_metrics`` JSONB 컬럼은
``{ category_name: CategoryMetrics }`` 구조로 직렬화되어 저장되며, 프론트엔드는
같은 스키마로 역직렬화한다.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# 5축 카테고리 이름 — analysis_results.categories[] 컬럼과 동일.
CategoryName = Literal[
    "technical", "structured", "content", "authority", "visibility"
]
ALL_CATEGORIES: tuple[CategoryName, ...] = (
    "technical", "structured", "content", "authority", "visibility",
)

ImprovementPriority = Literal["high", "medium", "low"]
ImprovementEffort   = Literal["low", "medium", "high"]


# 메트릭 값은 boolean / 숫자 / 문자열 / null 모두 허용.
# Pydantic v2는 Union 직렬화를 안정 처리.
MetricValue = bool | int | float | str | None


class MetricResult(BaseModel):
    """단일 메트릭 측정 결과 (SPEC §7-2)."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(
        description="안정 식별자 — 변경 ❌, 새 키 추가만 (예: 'ssl_enabled')"
    )
    display_name_key: str = Field(
        description="i18n 사전 키 — 프론트엔드 라벨"
    )
    description_key: str = Field(
        description="i18n 사전 키 — 프론트엔드 설명"
    )
    value: MetricValue = Field(
        default=None,
        description="측정값 (bool / 숫자 / 문자열 / null)"
    )
    weight: float = Field(
        ge=0.0, le=1.0,
        description="카테고리 내 메트릭 가중치 (0~1, 카테고리 합계 = 1.0)"
    )
    passed: bool = Field(
        description="threshold 기준 통과 여부 (점수 환산: passed=1.0 / fail=0.0)"
    )
    threshold: float | None = Field(
        default=None,
        description="passed 판정 기준 (선택)"
    )
    evidence: str | None = Field(
        default=None,
        description="원시 데이터/디버깅 메모 (선택)"
    )


class CategoryMetrics(BaseModel):
    """카테고리 단위 결과 — 메트릭 리스트 + 가중평균 점수 (SPEC §7-2).

    ``score`` 는 ``metrics`` 의 ``passed`` × ``weight`` 합 × 100 (0~100 정수화 권장).
    ``analyze()`` 호출자가 직접 계산해도 되고 ``compute_score()`` 헬퍼 사용도 가능.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    score: float = Field(
        ge=0.0, le=100.0,
        description="가중평균 점수 (0~100)"
    )
    metrics: list[MetricResult] = Field(
        description="이 카테고리의 모든 메트릭 결과 (순서 = 표시 순서)"
    )

    @model_validator(mode="after")
    def _check_weights_sum(self) -> "CategoryMetrics":
        """metrics[].weight 합은 1.0 ± 1e-3 이어야 함 (가중평균이 0~100에 매핑)."""
        if not self.metrics:
            return self
        total = sum(m.weight for m in self.metrics)
        if abs(total - 1.0) > 1e-3:
            raise ValueError(
                f"category metric weights must sum to 1.0, got {total:.4f}"
            )
        return self


def compute_score(metrics: list[MetricResult]) -> float:
    """``MetricResult`` 리스트에서 0~100 가중평균 점수 계산.

    skeleton/stub MetricResult는 passed=False 이므로 자연히 0.0이 산출됨.
    weight 합이 1.0이 아니면 ValueError (CategoryMetrics validator와 동일 규칙).
    """
    if not metrics:
        return 0.0
    total_weight = sum(m.weight for m in metrics)
    if abs(total_weight - 1.0) > 1e-3:
        raise ValueError(
            f"metric weights must sum to 1.0, got {total_weight:.4f}"
        )
    score = sum((1.0 if m.passed else 0.0) * m.weight for m in metrics) * 100.0
    # 0.01 단위로 라운드 — JSONB 안정 직렬화.
    return round(score, 2)


class Improvement(BaseModel):
    """개선 제안 (SPEC §7-2). LLM 통합 호출(G3 services/llm_synthesizer)이 생성.

    ``description`` 은 lang→string 매핑(LLM 동적 생성). ``title_key`` 는 정적
    케이스에 한해 i18n 사전 키.
    """
    model_config = ConfigDict(extra="forbid", frozen=True)

    priority: ImprovementPriority
    category: CategoryName
    title_key: str = Field(description="i18n 사전 키 (정적 케이스)")
    description: dict[str, str] = Field(
        description="lang(en/ko/es) → 설명 (LLM 동적 생성)"
    )
    estimated_impact: int = Field(ge=1, le=10)
    estimated_effort: ImprovementEffort
    related_metric_keys: list[str] = Field(
        description="이 개선과 연결된 메트릭 키들 (UI에서 메트릭 → 개선 링크)"
    )


class AnalysisOptions(BaseModel):
    """``analyze(url, options)`` 의 옵션 — 카테고리 모듈 공통.

    무거운/외부의존 체크(PSI / WHOIS / LLM 호출)는 기본 OFF. G3/G4에서 라우터
    플래그 또는 환경변수로 ON.
    """
    model_config = ConfigDict(extra="forbid")

    timeout_seconds: float = Field(
        default=30.0, gt=0.0,
        description="HTTP 요청 단일 타임아웃"
    )
    user_agent: str = Field(
        default="aeo-visibility/2.0 (+https://aeo.example.com)",
        description="크롤러 User-Agent"
    )
    enable_external_apis: bool = Field(
        default=False,
        description="PSI/WHOIS 등 외부 API 호출 허용 (Phase 1 skeleton은 항상 stub)"
    )
    enable_llm_visibility: bool = Field(
        default=False,
        description="visibility 카테고리에서 Claude API 호출 (G3 이후)"
    )
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="확장용 — 카테고리 모듈이 자유 사용"
    )
