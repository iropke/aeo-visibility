"""리포트 라우터 — PDF/CSV 다운로드 메타 (Phase 1 stub).

엔드포인트:
    GET    /api/workspaces/{workspace_id}/reports                         목록 (viewer+)
    POST   /api/workspaces/{workspace_id}/reports                         생성 + BG 렌더 (member+ writable)
    GET    /api/workspaces/{workspace_id}/reports/{report_id}             단건
    GET    /api/workspaces/{workspace_id}/reports/{report_id}/download    signed URL 발급 (Phase 1 stub)
    DELETE /api/workspaces/{workspace_id}/reports/{report_id}             메타 삭제 (admin+)

Phase 1 메모:
    - 실 PDF/CSV 렌더는 Phase 3. 본 라우터는 메타 + 상태 전이 + 다운로드 계약만.
    - POST 는 즉시 ``201 Created`` + status='pending' 반환. report_task 가 BG 에서
      status='ready' 로 마크 (placeholder storage_path).
    - GET /download 는 status 별 분기:
        pending → 425 Too Early
        failed  → 410 Gone (error_message 포함)
        ready   → 200 + ``ReportDownloadResponse(stub=True)`` (download_url=None).
                  Phase 3 에서 실 signed URL + expires_at 채움.
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import AuthenticatedUser
from app.deps import (
    DbSession,
    require_workspace_role,
    require_writable_workspace_role,
)
from app.models.analysis_result import AnalysisResult
from app.models.database import async_session
from app.models.report import Report, ReportStatus
from app.models.workspace import WorkspaceRole
from app.schemas.report import (
    ReportCreate,
    ReportDownloadResponse,
    ReportResponse,
)
from app.tasks.report_task import run_report_render


router = APIRouter(prefix="/api/workspaces", tags=["reports"])


# ── dep aliases ──────────────────────────────────────────────────

# 조회 — viewer+ 가능, 트라이얼 만료에서도 read 허용.
ViewCtx = Annotated[
    tuple[AuthenticatedUser, WorkspaceRole],
    Depends(require_workspace_role(WorkspaceRole.viewer)),
]
# 생성 — member+ + writable (트라이얼 만료/해지 시 402).
CreateCtx = Annotated[
    tuple[AuthenticatedUser, WorkspaceRole],
    Depends(require_writable_workspace_role(WorkspaceRole.member)),
]
# 삭제 — admin+ + writable.
DeleteCtx = Annotated[
    tuple[AuthenticatedUser, WorkspaceRole],
    Depends(require_writable_workspace_role(WorkspaceRole.admin)),
]


# ── helpers ──────────────────────────────────────────────────────

async def _get_report(
    db: AsyncSession, workspace_id: UUID, report_id: UUID,
) -> Report:
    report = await db.scalar(
        select(Report).where(
            Report.id == report_id,
            Report.workspace_id == workspace_id,
        )
    )
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    return report


async def _validate_analysis_belongs(
    db: AsyncSession, workspace_id: UUID, analysis_id: UUID,
) -> None:
    """analysis_id 가 해당 워크스페이스 소유인지 검증. 아니면 404."""
    exists = await db.scalar(
        select(AnalysisResult.id).where(
            AnalysisResult.id == analysis_id,
            AnalysisResult.workspace_id == workspace_id,
        )
    )
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis result not found in this workspace",
        )


# ── endpoints ────────────────────────────────────────────────────


@router.get(
    "/{workspace_id}/reports",
    response_model=list[ReportResponse],
)
async def list_reports(
    workspace_id: UUID,
    ctx: ViewCtx,
    db: DbSession,
    limit: int = 50,
    offset: int = 0,
) -> list[ReportResponse]:
    """워크스페이스의 리포트 목록 (최신순). viewer+ 가능."""
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

    rows = (
        await db.execute(
            select(Report)
            .where(Report.workspace_id == workspace_id)
            .order_by(desc(Report.requested_at))
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return [ReportResponse.model_validate(r) for r in rows]


@router.post(
    "/{workspace_id}/reports",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_report(
    workspace_id: UUID,
    payload: ReportCreate,
    ctx: CreateCtx,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> ReportResponse:
    """리포트 생성 트리거. status='pending' 즉시 반환 + BG 렌더.

    Phase 1: report_task 가 placeholder 메타 채움 (실 파일 ❌).
    Phase 3: 실제 PDF/CSV 렌더 + Supabase Storage 업로드.
    """
    user, _role = ctx

    # analysis_id 가 set 되면 동일 워크스페이스 소유인지 검증 (cross-tenant 차단).
    if payload.analysis_id is not None:
        await _validate_analysis_belongs(db, workspace_id, payload.analysis_id)

    report = Report(
        workspace_id=workspace_id,
        analysis_id=payload.analysis_id,
        format=payload.format,
        status=ReportStatus.pending,
        requested_by=user.id,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # 응답 직후 BackgroundTasks 가 별도 세션에서 실행. tx commit 후이므로
    # task 가 row 를 정상 SELECT/UPDATE 가능.
    background_tasks.add_task(
        run_report_render,
        async_session,
        report_id=report.id,
        workspace_id=workspace_id,
    )
    return ReportResponse.model_validate(report)


@router.get(
    "/{workspace_id}/reports/{report_id}",
    response_model=ReportResponse,
)
async def get_report(
    workspace_id: UUID,
    report_id: UUID,
    ctx: ViewCtx,
    db: DbSession,
) -> ReportResponse:
    """리포트 단건 조회. 폴링 대상 (status 전이 확인용)."""
    _ = ctx
    report = await _get_report(db, workspace_id, report_id)
    return ReportResponse.model_validate(report)


@router.get(
    "/{workspace_id}/reports/{report_id}/download",
    response_model=ReportDownloadResponse,
)
async def get_report_download(
    workspace_id: UUID,
    report_id: UUID,
    ctx: ViewCtx,
    db: DbSession,
) -> ReportDownloadResponse:
    """다운로드 URL 발급.

    상태별 응답:
      pending → 425 Too Early (아직 렌더 중)
      failed  → 410 Gone (error_message 포함)
      ready   → 200 + ReportDownloadResponse(stub=True, download_url=None) [Phase 1]
                Phase 3 에서 실 Supabase Storage signed URL + expires_at 채움.
    """
    _ = ctx
    report = await _get_report(db, workspace_id, report_id)

    if report.status == ReportStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail="Report is still being generated; poll /reports/{id}",
        )
    if report.status == ReportStatus.failed:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=report.error_message or "Report generation failed",
        )

    # status == 'ready' — Phase 1 stub 응답.
    return ReportDownloadResponse(
        report_id=report.id,
        format=report.format,
        status=report.status,
        download_url=None,
        expires_at=None,
        stub=True,
    )


@router.delete(
    "/{workspace_id}/reports/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_report(
    workspace_id: UUID,
    report_id: UUID,
    ctx: DeleteCtx,
    db: DbSession,
) -> None:
    """리포트 메타 삭제 (admin+).

    Phase 3: storage_path 의 객체도 함께 삭제 (Supabase Storage delete API).
    Phase 1 stub: row 만 hard delete.
    """
    _ = ctx
    report = await _get_report(db, workspace_id, report_id)
    await db.delete(report)
    await db.commit()
