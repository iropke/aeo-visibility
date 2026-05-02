"""analysis_results ORM 모델 + ENUM.

5축 카테고리 분석 결과 (1 row = 1 분석 실행). SPEC §5 / §7-2 표준 스키마 정합.

trigger_type:
  - 'auto'    — 매월 자동 cron (Phase 2 016_pg_cron_setup)
  - 'manual'  — 사용자 트리거 (Custom Re-analyze)

funding_source:
  - 'auto'        — 매월 cron (차감 ❌)
  - 'base'        — workspace.plan.custom_analyses_per_month 차감
  - 'basic_pack'  — custom_pack_basic addon (+5/월)
  - 'pro_pack'    — custom_pack_pro addon (+20/월)
  - 'payg'        — payg_custom 단건 PAYG ($2.99/회)

차감 우선순위(라우터 G3): pro_pack → basic_pack → base → payg.

INSERT/UPDATE는 BackgroundTasks(service_role) 전담. SQLAlchemy 모델은
일반 사용자 SELECT에서 읽기 전용으로 사용.
"""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    ARRAY,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AnalysisTriggerType(str, enum.Enum):
    """Postgres analysis_trigger_type ENUM 미러링."""
    auto = "auto"
    manual = "manual"


class AnalysisFundingSource(str, enum.Enum):
    """Postgres analysis_funding_source ENUM 미러링."""
    auto = "auto"
    base = "base"
    basic_pack = "basic_pack"
    pro_pack = "pro_pack"
    payg = "payg"


class AnalysisStatus(str, enum.Enum):
    """Postgres analysis_status ENUM 미러링."""
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    site_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
    )
    trigger_type: Mapped[AnalysisTriggerType] = mapped_column(
        SAEnum(
            AnalysisTriggerType,
            name="analysis_trigger_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    funding_source: Mapped[AnalysisFundingSource] = mapped_column(
        SAEnum(
            AnalysisFundingSource,
            name="analysis_funding_source",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    triggered_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("profiles.id"),
        nullable=True,
    )
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    categories: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False
    )
    overall_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    category_scores: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    raw_metrics: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    insights: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    improvements: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    analysis_version: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AnalysisStatus] = mapped_column(
        SAEnum(
            AnalysisStatus,
            name="analysis_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=AnalysisStatus.queued,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
