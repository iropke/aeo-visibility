"""분석(Custom Re-analyze) 라우터.

엔드포인트:
    POST /api/workspaces/{workspace_id}/sites/{site_id}/analyze
        Custom 재분석 트리거. body.categories=None → 5축 전체 (Full),
        부분 지정 → 해당 카테고리만. ``202 Accepted`` + status='queued' 즉시 반환,
        실제 분석은 BackgroundTasks 에서 비동기 실행. 클라이언트는 GET 디테일을
        polling 하여 status='completed'/'failed' 확인.
        Pack 차감 우선순위: pro_pack → basic_pack → base → payg.

    GET  /api/workspaces/{workspace_id}/sites/{site_id}/analyses
        해당 사이트의 분석 결과 목록 (최신순). limit/offset 페이징.

    GET  /api/workspaces/{workspace_id}/sites/{site_id}/analyses/{result_id}
        분석 결과 디테일 (raw_metrics + insights + improvements 포함). polling 대상.

    GET  /api/workspaces/{workspace_id}/analyses/active
        워크스페이스 단위 진행 중(queued|running) 분석 목록. 폴링 시 빈 리스트 = 모두 완료.

    GET  /api/workspaces/{workspace_id}/usage/current
        현재 월 quota 잔여 (프론트엔드 표시용). viewer+.

라우터 enforce 규칙 (SPEC §4-5 / §7-5 / §10):
    - viewer 트리거 차단 (행위 단위 가드: WorkspaceAction.analysis_trigger).
    - 트라이얼 만료/해지 게이팅 (require_action(writable=True) → 402).
    - 1시간 cooldown — sites.last_analyzed_at 기준.
    - 워크스페이스 진행 중 분석 1건 제한:
        * 1차: SELECT count 검사 (UX 좋은 빠른 fail).
        * 2차: partial UNIQUE index ``uniq_analysis_results_workspace_active``
               (013 마이그레이션) → race window 안전망. IntegrityError → 409.
    - quota 결정 + 차감 + INSERT 를 같은 트랜잭션 + monthly_usage row lock.

분석 실행은 ``app.tasks.analysis_task.run_analysis`` 가 BackgroundTasks 에서
호출. 라우터 트랜잭션이 commit되어 status='queued' row가 가시화된 뒤에 실행됨
(FastAPI BackgroundTasks 는 응답 직후 실행).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import AuthenticatedUser
from app.auth.permissions import WorkspaceAction
from app.deps import DbSession, require_action
from app.models.analysis_result import (
    AnalysisFundingSource,
    AnalysisResult,
    AnalysisStatus,
    AnalysisTriggerType,
)
from app.models.database import async_session
from app.models.site import Site
from app.models.workspace import WorkspaceRole
from app.schemas.analysis import (
    ActiveAnalysisItem,
    AnalysisResultDetail,
    AnalysisResultListItem,
    AnalyzeRequest,
    QuotaResponse,
)
from app.scoring import ANALYSIS_VERSION
from app.services.usage_service import (
    InsufficientQuotaError,
    current_year_month,
    get_quota_snapshot,
    increment_used,
    select_funding_source,
    upsert_and_lock_usage_row,
)
from app.tasks.analysis_task import run_analysis


router = APIRouter(prefix="/api/workspaces", tags=["analyses"])


# 1시간 — Custom Re-analyze 사이트당 cooldown.
ANALYZE_COOLDOWN = timedelta(hours=1)

# 진행 중 카운트 대상 status.
_ACTIVE_STATUSES = (AnalysisStatus.queued, AnalysisStatus.running)


# ── dep aliases ──────────────────────────────────────────────────

# Custom 분석 트리거 — viewer 차단 + 트라이얼 게이팅 + member+.
TriggerCtx = Annotated[
    tuple[AuthenticatedUser, WorkspaceRole],
    Depends(require_action(WorkspaceAction.analysis_trigger)),
]
# 분석 결과 조회 — viewer+ 가능, 트라이얼 만료에서도 read 허용.
ViewCtx = Annotated[
    tuple[AuthenticatedUser, WorkspaceRole],
    Depends(require_action(WorkspaceAction.analysis_view, writable=False)),
]


# ── helpers ──────────────────────────────────────────────────────


async def _get_active_site(
    db: AsyncSession, workspace_id: UUID, site_id: UUID
) -> Site:
    site = await db.scalar(
        select(Site).where(
            Site.id == site_id,
            Site.workspace_id == workspace_id,
            Site.deleted_at.is_(None),
        )
    )
    if site is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found",
        )
    return site


def _check_cooldown(site: Site) -> None:
    """1시간 cooldown — sites.last_analyzed_at 기준."""
    if site.last_analyzed_at is None:
        return
    elapsed = datetime.now(timezone.utc) - site.last_analyzed_at
    if elapsed < ANALYZE_COOLDOWN:
        retry_after = ANALYZE_COOLDOWN - elapsed
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Analysis cooldown active for this site; retry in "
                f"{int(retry_after.total_seconds())}s"
            ),
        )


async def _check_no_active_analysis(
    db: AsyncSession, workspace_id: UUID
) -> None:
    """워크스페이스 단위 진행 중 분석 1건 제한.

    Phase 1: SELECT 후 INSERT 흐름 — race 윈도우 존재. Redis lock 도입은 G4.
    동시 호출 빈도가 낮은 사용자 트리거이므로 SELECT 검사로 충분.
    """
    active_count = await db.scalar(
        select(func.count(AnalysisResult.id)).where(
            AnalysisResult.workspace_id == workspace_id,
            AnalysisResult.status.in_(_ACTIVE_STATUSES),
        )
    )
    if active_count and active_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another analysis is already in progress for this workspace",
        )


# ── endpoints ────────────────────────────────────────────────────


@router.post(
    "/{workspace_id}/sites/{site_id}/analyze",
    response_model=AnalysisResultDetail,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_analysis(
    workspace_id: UUID,
    site_id: UUID,
    payload: AnalyzeRequest,
    ctx: TriggerCtx,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> AnalysisResultDetail:
    """Custom Re-analyze 트리거.

    응답: 202 Accepted + status='queued' analysis row. 실 분석은 BackgroundTasks
    에서 비동기 실행 — 클라이언트는 GET 디테일/active 로 polling.
    """
    user, _role = ctx

    site = await _get_active_site(db, workspace_id, site_id)
    _check_cooldown(site)
    await _check_no_active_analysis(db, workspace_id)

    try:
        categories = payload.normalized_categories()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    year_month = current_year_month()
    usage_row = await upsert_and_lock_usage_row(db, workspace_id, year_month)
    snapshot = await get_quota_snapshot(
        db, workspace_id, usage_row=usage_row, year_month=year_month
    )

    try:
        funding_source = select_funding_source(snapshot, allow_payg=payload.allow_payg)
    except InsufficientQuotaError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(exc),
        ) from exc

    # 차감 + analysis_result INSERT (같은 tx).
    increment_used(usage_row, funding_source)

    analysis = AnalysisResult(
        workspace_id=workspace_id,
        site_id=site_id,
        trigger_type=AnalysisTriggerType.manual,
        funding_source=funding_source,
        triggered_by=user.id,
        categories=list(categories),
        analysis_version=ANALYSIS_VERSION,
        status=AnalysisStatus.queued,
    )
    db.add(analysis)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        # uniq_analysis_results_workspace_active (013) — race 안전망.
        # 동시 두 트리거가 SELECT count 검사를 동시 통과 → 한 쪽이 INSERT 시
        # partial UNIQUE index 충돌 → 409로 변환.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another analysis is already in progress for this workspace",
        ) from exc
    await db.refresh(analysis)

    # 응답 직후 BackgroundTasks 가 별도 세션에서 실행. 라우터 tx 가 commit 된 뒤이므로
    # task가 row를 정상 SELECT/UPDATE 가능.
    background_tasks.add_task(
        run_analysis,
        async_session,
        analysis_id=analysis.id,
        site_id=site_id,
        workspace_id=workspace_id,
        site_url=site.url,
        categories=categories,
    )
    return AnalysisResultDetail.model_validate(analysis)


@router.get(
    "/{workspace_id}/sites/{site_id}/analyses",
    response_model=list[AnalysisResultListItem],
)
async def list_analyses(
    workspace_id: UUID,
    site_id: UUID,
    ctx: ViewCtx,
    db: DbSession,
    limit: int = 50,
    offset: int = 0,
) -> list[AnalysisResultListItem]:
    """사이트의 분석 결과 목록 (최신순). viewer+ 가능. 트라이얼 만료에서도 read 가능."""
    _ = ctx
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be between 1 and 200",
        )
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="offset must be >= 0",
        )

    # 사이트 존재 + 워크스페이스 소속 검증 (soft-deleted도 조회 가능 — 과거 결과).
    site = await db.scalar(
        select(Site.id).where(
            Site.id == site_id, Site.workspace_id == workspace_id
        )
    )
    if site is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Site not found"
        )

    rows = (
        await db.execute(
            select(AnalysisResult)
            .where(
                AnalysisResult.site_id == site_id,
                AnalysisResult.workspace_id == workspace_id,
            )
            .order_by(desc(AnalysisResult.triggered_at))
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return [AnalysisResultListItem.model_validate(r) for r in rows]


@router.get(
    "/{workspace_id}/sites/{site_id}/analyses/{result_id}",
    response_model=AnalysisResultDetail,
)
async def get_analysis(
    workspace_id: UUID,
    site_id: UUID,
    result_id: UUID,
    ctx: ViewCtx,
    db: DbSession,
) -> AnalysisResultDetail:
    """분석 결과 디테일 (raw_metrics + insights + improvements 포함)."""
    _ = ctx
    row = await db.scalar(
        select(AnalysisResult).where(
            AnalysisResult.id == result_id,
            AnalysisResult.site_id == site_id,
            AnalysisResult.workspace_id == workspace_id,
        )
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis result not found",
        )
    return AnalysisResultDetail.model_validate(row)


@router.get(
    "/{workspace_id}/analyses/active",
    response_model=list[ActiveAnalysisItem],
)
async def list_active_analyses(
    workspace_id: UUID,
    ctx: ViewCtx,
    db: DbSession,
) -> list[ActiveAnalysisItem]:
    """워크스페이스 단위 진행 중(queued|running) 분석 목록.

    빈 리스트 = 모두 완료 (폴링 종료 신호). partial UNIQUE index 보장으로 0~1개.
    """
    _ = ctx
    rows = (
        await db.execute(
            select(AnalysisResult)
            .where(
                AnalysisResult.workspace_id == workspace_id,
                AnalysisResult.status.in_(_ACTIVE_STATUSES),
            )
            .order_by(desc(AnalysisResult.triggered_at))
        )
    ).scalars().all()
    return [ActiveAnalysisItem.model_validate(r) for r in rows]


@router.get(
    "/{workspace_id}/usage/current",
    response_model=QuotaResponse,
)
async def get_current_usage(
    workspace_id: UUID,
    ctx: ViewCtx,
    db: DbSession,
) -> QuotaResponse:
    """현재 월 quota 잔여 — 프론트엔드 잔여 횟수 표시용. viewer+."""
    _ = ctx
    snapshot = await get_quota_snapshot(db, workspace_id)
    return QuotaResponse(
        year_month=snapshot.year_month,
        pro_pack={
            "quota": snapshot.pro_pack_quota,
            "used": snapshot.pro_pack_used,
            "remaining": snapshot.remaining(AnalysisFundingSource.pro_pack),
        },
        basic_pack={
            "quota": snapshot.basic_pack_quota,
            "used": snapshot.basic_pack_used,
            "remaining": snapshot.remaining(AnalysisFundingSource.basic_pack),
        },
        base={
            "quota": snapshot.base_quota,
            "used": snapshot.base_used,
            "remaining": snapshot.remaining(AnalysisFundingSource.base),
        },
        payg_used=snapshot.payg_used,
    )
