"""subscriptions API I/O 스키마."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.subscription import SubscriptionStatus


class SubscriptionResponse(BaseModel):
    """워크스페이스의 현재 구독 상태 — 트라이얼 카운트다운 / 결제 화면 표시용.

    Phase 1 사용처:
        - AppHeader 트라이얼 잔여 일수 배지
        - TrialExpiryModal 트리거 (≤3일)
        - Phase 2 Pricing/Checkout/Customer Portal 진입 데이터
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    plan_id: str
    status: SubscriptionStatus
    billing_cycle: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    canceled_at: datetime | None
    trial_ends_at: datetime | None
    created_at: datetime
    updated_at: datetime
