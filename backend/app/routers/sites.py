"""사이트 라우터 — 자사/경쟁사 사이트 CRUD.

엔드포인트:
    GET    /api/workspaces/{workspace_id}/sites                 활성 사이트 목록
    POST   /api/workspaces/{workspace_id}/sites                 사이트 추가 (member+)
    GET    /api/workspaces/{workspace_id}/sites/{site_id}       단건 조회
    PATCH  /api/workspaces/{workspace_id}/sites/{site_id}       URL/닉네임 수정 (member+)
    DELETE /api/workspaces/{workspace_id}/sites/{site_id}       soft delete (owner/admin)

라우터에서 enforce 하는 비즈니스 규칙 (SPEC §4-5):
    - max_sites (자사) — plans.max_sites (음수 = 무제한)
    - competitors_per_site — 워크스페이스 내 경쟁사 합계 ≤ own_count × competitors_per_site
        (사이트별 부모 매핑은 Phase 3에서 parent_site_id 도입 예정)
    - 동일 워크스페이스 내 동일 도메인 활성 1건 (DB UNIQUE partial index)
    - 30일 도메인 cooldown — soft-deleted 사이트의 ``delete_cooldown_until`` 초과까지 재등록 차단
    - URL 교체 1회/월 — 워크스페이스 내 어느 사이트든 last_url_changed_at > NOW()-30일이면 차단.
        단, 대상 사이트의 ``last_analyzed_at`` IS NULL이면 무료 변경 (첫 분석 전 예외).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import AuthenticatedUser
from app.deps import (
    DbSession,
    require_workspace_role,
    require_writable_workspace_role,
)
from app.models.plan import Plan
from app.models.site import Site, SiteType
from app.models.workspace import Workspace, WorkspaceRole
from app.schemas.site import SiteCreate, SiteResponse, SiteUpdate, normalize_domain

router = APIRouter(prefix="/api/workspaces", tags=["sites"])


WorkspaceMemberCtx = Annotated[
    tuple[AuthenticatedUser, WorkspaceRole],
    Depends(require_workspace_role(WorkspaceRole.viewer)),
]
# 쓰기 엔드포인트 — 트라이얼 만료/해지 시 402 차단.
WorkspaceWriterCtx = Annotated[
    tuple[AuthenticatedUser, WorkspaceRole],
    Depends(require_writable_workspace_role(WorkspaceRole.member)),
]
WorkspaceAdminCtx = Annotated[
    tuple[AuthenticatedUser, WorkspaceRole],
    Depends(require_writable_workspace_role(WorkspaceRole.admin)),
]


# ============================================================
# 헬퍼
# ============================================================


async def _get_workspace_plan(db: AsyncSession, workspace_id: UUID) -> Plan:
    plan = await db.scalar(
        select(Plan)
        .join(Workspace, Workspace.plan_id == Plan.id)
        .where(Workspace.id == workspace_id)
    )
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace or plan not found",
        )
    return plan


async def _count_active_sites(
    db: AsyncSession, workspace_id: UUID, site_type: SiteType
) -> int:
    return await db.scalar(
        select(func.count(Site.id)).where(
            Site.workspace_id == workspace_id,
            Site.type == site_type,
            Site.deleted_at.is_(None),
        )
    ) or 0


async def _check_domain_cooldown(
    db: AsyncSession, workspace_id: UUID, domain: str
) -> datetime | None:
    """동일 도메인이 30일 cooldown에 있으면 만료 시각, 없으면 None."""
    now = datetime.now(timezone.utc)
    return await db.scalar(
        select(Site.delete_cooldown_until).where(
            Site.workspace_id == workspace_id,
            Site.domain == domain,
            Site.delete_cooldown_until.isnot(None),
            Site.delete_cooldown_until > now,
        )
    )


async def _enforce_url_change_monthly_limit(
    db: AsyncSession, workspace_id: UUID, target_site: Site
) -> None:
    """워크스페이스 내 last_url_changed_at > NOW()-30일인 사이트가 있으면 429.

    예외: 대상 사이트의 ``last_analyzed_at`` IS NULL → 첫 분석 전 무료 변경.
    """
    if target_site.last_analyzed_at is None:
        return  # 분석 전 변경은 횟수 미차감.

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    recent_site_id = await db.scalar(
        select(Site.id).where(
            Site.workspace_id == workspace_id,
            Site.deleted_at.is_(None),
            Site.last_url_changed_at.isnot(None),
            Site.last_url_changed_at > cutoff,
        ).limit(1)
    )
    if recent_site_id is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="URL change limit reached: 1 change per workspace per 30 days",
        )


# ============================================================
# Endpoints
# ============================================================


@router.get(
    "/{workspace_id}/sites",
    response_model=list[SiteResponse],
)
async def list_sites(
    workspace_id: UUID,
    ctx: WorkspaceMemberCtx,
    db: DbSession,
    include_deleted: bool = False,
) -> list[SiteResponse]:
    _ = ctx
    stmt = select(Site).where(Site.workspace_id == workspace_id)
    if not include_deleted:
        stmt = stmt.where(Site.deleted_at.is_(None))
    stmt = stmt.order_by(Site.created_at.asc())
    rows = (await db.execute(stmt)).scalars().all()
    return [SiteResponse.model_validate(s) for s in rows]


@router.post(
    "/{workspace_id}/sites",
    response_model=SiteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_site(
    workspace_id: UUID,
    payload: SiteCreate,
    ctx: WorkspaceWriterCtx,
    db: DbSession,
) -> SiteResponse:
    plan = await _get_workspace_plan(db, workspace_id)
    domain = normalize_domain(str(payload.url))
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract domain from URL",
        )

    # 1) max_sites 한도 (자사 / 경쟁사 분리)
    if payload.type == SiteType.own:
        if plan.max_sites != -1:
            count = await _count_active_sites(db, workspace_id, SiteType.own)
            if count >= plan.max_sites:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Plan '{plan.id}' allows at most {plan.max_sites} own site(s); add-on or upgrade required",
                )
    else:  # competitor
        if plan.competitors_per_site == 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Plan '{plan.id}' does not include competitor sites; upgrade to Pro or higher",
            )
        if plan.competitors_per_site != -1:
            own_count = await _count_active_sites(db, workspace_id, SiteType.own)
            comp_count = await _count_active_sites(db, workspace_id, SiteType.competitor)
            cap = own_count * plan.competitors_per_site
            if comp_count >= cap:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Plan '{plan.id}' allows {plan.competitors_per_site} competitor(s) "
                        f"per own site (current cap: {cap})"
                    ),
                )

    # 2) 30일 cooldown 검사
    cooldown_until = await _check_domain_cooldown(db, workspace_id, domain)
    if cooldown_until is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Domain '{domain}' is in cooldown until {cooldown_until.isoformat()} (30-day rule after delete)",
        )

    site = Site(
        workspace_id=workspace_id,
        url=str(payload.url),
        domain=domain,
        nickname=payload.nickname,
        type=payload.type,
    )
    db.add(site)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        # uniq_sites_workspace_domain_active 위배 — 동일 도메인 활성 사이트 이미 존재.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Domain '{domain}' is already registered as an active site in this workspace",
        ) from exc

    await db.refresh(site)
    return SiteResponse.model_validate(site)


@router.get(
    "/{workspace_id}/sites/{site_id}",
    response_model=SiteResponse,
)
async def get_site(
    workspace_id: UUID,
    site_id: UUID,
    ctx: WorkspaceMemberCtx,
    db: DbSession,
) -> SiteResponse:
    _ = ctx
    site = await db.scalar(
        select(Site).where(
            Site.id == site_id,
            Site.workspace_id == workspace_id,
        )
    )
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return SiteResponse.model_validate(site)


@router.patch(
    "/{workspace_id}/sites/{site_id}",
    response_model=SiteResponse,
)
async def update_site(
    workspace_id: UUID,
    site_id: UUID,
    payload: SiteUpdate,
    ctx: WorkspaceWriterCtx,
    db: DbSession,
) -> SiteResponse:
    site = await db.scalar(
        select(Site).where(
            Site.id == site_id,
            Site.workspace_id == workspace_id,
            Site.deleted_at.is_(None),
        )
    )
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    updates = payload.model_dump(exclude_unset=True)
    new_url = updates.get("url")

    if new_url is not None:
        new_url_str = str(new_url)
        new_domain = normalize_domain(new_url_str)
        if not new_domain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract domain from URL",
            )

        if new_domain != site.domain:
            # 워크스페이스 단위 1회/월 한도 (last_analyzed_at IS NULL이면 면제).
            await _enforce_url_change_monthly_limit(db, workspace_id, site)
            # 새 도메인이 cooldown 중인지 검사.
            cooldown_until = await _check_domain_cooldown(db, workspace_id, new_domain)
            if cooldown_until is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Domain '{new_domain}' is in cooldown until {cooldown_until.isoformat()}",
                )
            site.domain = new_domain
            site.last_url_changed_at = datetime.now(timezone.utc)

        site.url = new_url_str

    if "nickname" in updates:
        site.nickname = updates["nickname"]

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Domain conflict: another active site with the same domain exists",
        ) from exc

    await db.refresh(site)
    return SiteResponse.model_validate(site)


@router.delete(
    "/{workspace_id}/sites/{site_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_site(
    workspace_id: UUID,
    site_id: UUID,
    ctx: WorkspaceAdminCtx,
    db: DbSession,
) -> None:
    """soft delete — ``deleted_at`` + ``delete_cooldown_until`` 만 set.

    실제 row 제거는 향후 grace_processor cron이 cooldown 만료 후 처리.
    """
    _ = ctx
    site = await db.scalar(
        select(Site).where(
            Site.id == site_id,
            Site.workspace_id == workspace_id,
            Site.deleted_at.is_(None),
        )
    )
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    now = datetime.now(timezone.utc)
    site.deleted_at = now
    site.delete_cooldown_until = now + timedelta(days=30)
    await db.commit()
