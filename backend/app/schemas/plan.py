"""plans API I/O 스키마.

라우터: ``app.routers.plans`` (GET /api/plans, public 인증 ❌).
DB 모델: ``app.models.plan.Plan``.

쿠폰 미적용 raw 가격을 그대로 반환. Phase 2 쿠폰 청크에서 ``price_after_coupon``
필드 추가 + active 쿠폰 적용 로직이 service 레이어에 들어옴 (인터페이스 변경 ❌).

Stripe price_id 노출 ❌ — 결제 라우터(Phase 2)에서만 사용.
``-1`` 컬럼값 = 무제한 표기 (frontend 가 i18n 으로 "Unlimited" 등으로 표시).
"""
from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PlanRead(BaseModel):
    """GET /api/plans 응답 element."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    price_monthly_usd: Decimal
    price_annual_usd: Decimal | None
    max_sites: int
    max_competitors: int
    max_members_default: int
    max_members_hardcap: int
    custom_analyses_per_month: int
    timeseries_months: int
    csv_export: bool
    competitor_comparison: bool
    competitor_trend_graph: bool
    default_ai_engines: int
    competitors_per_site: int
    industry_benchmark: bool
    audit_log_days: int
    data_retention_years: int
    support_tier: str
    is_enterprise: bool
    is_active: bool
