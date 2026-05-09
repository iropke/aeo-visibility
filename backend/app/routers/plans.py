"""Plans 라우터 — public 가격표 조회.

엔드포인트:
    GET /api/plans   — 활성 플랜 목록 (인증 ❌). Pricing 페이지가 fetch.

Phase 2 쿠폰 청크에서 active 쿠폰 적용가를 반환하도록 service 레이어 1줄 교체.
인터페이스 변경 ❌ — frontend 도 그대로 사용 가능.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.plan import Plan
from app.schemas.plan import PlanRead

router = APIRouter(prefix="/api/plans", tags=["plans"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

# Pricing 페이지 정렬: free → basic → pro → business → enterprise.
# is_active=true 만 반환. Phase 2 쿠폰 청크에서 가격 변형 가능 (스키마 동일).
_PLAN_DISPLAY_ORDER: dict[str, int] = {
    "free": 0,
    "basic": 1,
    "pro": 2,
    "business": 3,
    "enterprise": 4,
}


@router.get("", response_model=list[PlanRead])
async def list_plans(db: DbSession) -> list[Plan]:
    """활성 플랜 전체 반환. 정렬은 ``_PLAN_DISPLAY_ORDER``, 미등록 id 는 마지막."""
    result = await db.execute(
        select(Plan).where(Plan.is_active.is_(True))
    )
    plans = list(result.scalars().all())
    plans.sort(key=lambda p: _PLAN_DISPLAY_ORDER.get(p.id, 99))
    return plans
