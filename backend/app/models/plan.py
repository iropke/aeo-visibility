"""plans ORM 모델 — 구독 플랜 마스터."""
from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    price_monthly_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_annual_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_sites: Mapped[int] = mapped_column(Integer, nullable=False)
    max_competitors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_members_default: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_members_hardcap: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    custom_analyses_per_month: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    timeseries_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    csv_export: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    competitor_comparison: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    competitor_trend_graph: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 008_plans_repricing.sql 에서 추가된 컬럼들. -1 = 무제한 표기.
    default_ai_engines: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    competitors_per_site: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    industry_benchmark: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    audit_log_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_retention_years: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    support_tier: Mapped[str] = mapped_column(Text, nullable=False, default="self")
    is_enterprise: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stripe_price_id_monthly: Mapped[str | None] = mapped_column(Text, nullable=True)
    stripe_price_id_annual: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
