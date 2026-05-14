"""reports ORM 모델 + ENUM.

PDF/CSV 다운로드 메타 (1 row = 1 다운로드 요청). SPEC §5 reports + 016_reports.sql 정합.

format / status:
    format: 'pdf' | 'csv'
    status: 'pending' (큐) → 'ready' (다운로드 가능) | 'failed'

analysis_id:
    NOT NULL — 단일 분석 결과 리포트
    NULL     — 워크스페이스 종합 리포트 (Phase 3)

INSERT/UPDATE 는 라우터 / report_task(service_role) 전담. SELECT 만 RLS.
"""
from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ReportFormat(str, enum.Enum):
    """Postgres report_format ENUM 미러링."""
    pdf = "pdf"
    csv = "csv"


class ReportStatus(str, enum.Enum):
    """Postgres report_status ENUM 미러링."""
    pending = "pending"
    ready = "ready"
    failed = "failed"


class Report(Base):
    __tablename__ = "reports"

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
    analysis_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("analysis_results.id", ondelete="SET NULL"),
        nullable=True,
    )
    format: Mapped[ReportFormat] = mapped_column(
        SAEnum(
            ReportFormat,
            name="report_format",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    status: Mapped[ReportStatus] = mapped_column(
        SAEnum(
            ReportStatus,
            name="report_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ReportStatus.pending,
    )
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    requested_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("profiles.id"),
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
