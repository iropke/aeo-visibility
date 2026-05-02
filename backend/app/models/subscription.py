"""subscriptions ORM 모델 + SubscriptionStatus enum.

워크스페이스 1:N subscriptions (history 보존). 생성 시점에 자동으로
status='trial' + plan_id='free' + trial_ends_at=NOW()+7일 row가 트리거로 INSERT됨
(009_subscriptions.sql start_trial_for_new_workspace 참조).

Stripe 통합(Phase 2)은 service_role webhook이 status / stripe_subscription_id /
current_period_* / cancel_at_period_end / canceled_at 을 갱신.
"""
from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SubscriptionStatus(str, enum.Enum):
    """Postgres subscription_status ENUM 미러링."""
    trial = "trial"
    active = "active"
    past_due = "past_due"
    canceled = "canceled"
    paused = "paused"


class Subscription(Base):
    __tablename__ = "subscriptions"

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
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        Text, nullable=True, unique=True
    )
    plan_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("plans.id"),
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        # 마이그레이션에서 'subscription_status' ENUM으로 생성됨.
        # create_type=False: SQLAlchemy가 ENUM 재생성 시도하지 않도록.
        SAEnum(
            SubscriptionStatus,
            name="subscription_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=SubscriptionStatus.trial,
    )
    billing_cycle: Mapped[str] = mapped_column(
        Text, nullable=False, default="monthly"
    )
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    canceled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "billing_cycle IN ('monthly', 'annual')",
            name="subscriptions_billing_cycle_check",
        ),
    )
