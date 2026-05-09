"""contact_submissions ORM 모델 — 공개 Contact 폼 응답 저장.

마이그레이션: ``supabase/migrations/015_contact_submissions.sql``.
RLS: service_role only — 백엔드 라우터(``app.routers.contact``)만 접근.

처리 상태 라이프사이클: ``new`` → ``in_progress`` → ``resolved`` 또는 ``spam``.
Phase 1 운영자는 supabase 콘솔 SQL 로 status 변경. admin UI 는 별도 청크.
"""
from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ContactStatus(str, enum.Enum):
    """Postgres ``contact_status`` ENUM 미러링."""
    new = "new"
    in_progress = "in_progress"
    resolved = "resolved"
    spam = "spam"


class ContactTopic(str, enum.Enum):
    """Postgres ``contact_topic`` ENUM 미러링."""
    demo = "demo"
    sales = "sales"
    support = "support"
    general = "general"


class ContactSubmission(Base):
    __tablename__ = "contact_submissions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[ContactTopic] = mapped_column(
        SAEnum(
            ContactTopic,
            name="contact_topic",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ContactTopic.general,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    locale: Mapped[str] = mapped_column(Text, nullable=False, default="en")
    referrer_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ContactStatus] = mapped_column(
        SAEnum(
            ContactStatus,
            name="contact_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ContactStatus.new,
    )
    resolved_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
