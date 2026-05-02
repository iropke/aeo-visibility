"""monthly_usage ORM 모델.

워크스페이스 × YYYY-MM 단위 월간 사용량 카운터. SPEC §5 + 메모리의 funding source
분리 의도(base/basic_pack/pro_pack/payg)를 반영.

차감 라우터(G3 routers/analyses.py) 우선순위:
    pro_pack → basic_pack → base → payg

INSERT/UPDATE는 usage_service / 분석 task / 매월 cron(service_role) 전담.
일반 사용자는 자기 워크스페이스 SELECT만 (잔여 횟수 표시).
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MonthlyUsage(Base):
    __tablename__ = "monthly_usage"

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
    year_month: Mapped[str] = mapped_column(Text, nullable=False)  # 'YYYY-MM'
    base_analyses_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    basic_pack_analyses_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    pro_pack_analyses_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    payg_analyses_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    sites_changed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    qa_messages_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    auto_run_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "year_month",
            name="uniq_monthly_usage_workspace_month",
        ),
        CheckConstraint(
            r"year_month ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'",
            name="monthly_usage_year_month_format",
        ),
    )
