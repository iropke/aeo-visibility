"""analyses API I/O 스키마."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.analysis_result import (
    AnalysisFundingSource,
    AnalysisStatus,
    AnalysisTriggerType,
)
from app.scoring.schemas import ALL_CATEGORIES, CategoryName


class AnalyzeRequest(BaseModel):
    """POST /sites/{site}/analyze 요청 바디.

    categories=None 이면 5축 전체. 1개 이상 지정 시 해당 카테고리만 (Custom Re-analyze).
    """
    model_config = ConfigDict(extra="forbid")

    categories: list[CategoryName] | None = Field(
        default=None,
        description="분석할 카테고리 목록. None=전체 5축 (overall_score는 부분 분석 정규화)",
    )
    allow_payg: bool = Field(
        default=False,
        description="quota 소진 시 PAYG 단발 결제로 차감 허용. Phase 1은 결제 미연동이라 항상 ❌ 처리됨.",
    )

    def normalized_categories(self) -> list[CategoryName]:
        """None → 전체, 빈 리스트 → ValueError."""
        if self.categories is None:
            return list(ALL_CATEGORIES)
        if not self.categories:
            raise ValueError("categories must be None or a non-empty list")
        # 중복 제거하면서 입력 순서 보존.
        seen: dict[CategoryName, None] = {}
        for cat in self.categories:
            seen.setdefault(cat, None)
        return list(seen.keys())


class AnalysisResultListItem(BaseModel):
    """목록용 요약 — JSONB 무거운 필드 제외."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    site_id: UUID
    workspace_id: UUID
    trigger_type: AnalysisTriggerType
    funding_source: AnalysisFundingSource
    status: AnalysisStatus
    triggered_at: datetime
    completed_at: datetime | None
    duration_ms: int | None
    categories: list[str]
    overall_score: Decimal | None
    analysis_version: str


class AnalysisResultDetail(AnalysisResultListItem):
    """단건 디테일 — raw_metrics / insights / improvements 포함."""

    triggered_by: UUID | None
    category_scores: dict[str, Any] | None
    raw_metrics: dict[str, Any] | None
    insights: dict[str, Any] | None
    improvements: dict[str, Any] | None
    error_message: str | None


class QuotaResponse(BaseModel):
    """현재 월 quota 잔여 — 프론트엔드 잔여 횟수 표시.

    ``-1`` 은 무제한. payg는 ``unlimited`` (단발 결제).
    """
    year_month: str
    pro_pack: dict[str, int]   # {quota, used, remaining}  (-1 = unlimited)
    basic_pack: dict[str, int]
    base: dict[str, int]
    payg_used: int
