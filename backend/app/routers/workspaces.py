"""Workspace CRUD 라우터.

엔드포인트:
    GET    /api/workspaces                   현재 사용자의 워크스페이스 목록
    POST   /api/workspaces                   생성 (owner = 호출자)
    GET    /api/workspaces/{workspace_id}    단건 조회 (멤버만)
    PATCH  /api/workspaces/{workspace_id}    수정 (owner/admin)
    DELETE /api/workspaces/{workspace_id}    삭제 (owner)
                                             — 7일 grace는 Phase 2에서 추가, 현재는 hard delete.
"""
from __future__ import annotations

import re
import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.auth.jwt import AuthenticatedUser
from app.deps import (
    CurrentUser,
    DbSession,
    require_workspace_role,
)
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


# ============================================================
# Slug 생성 유틸
# ============================================================

_SLUG_INVALID_RE = re.compile(r"[^a-z0-9-]+")
_SLUG_DASH_RE = re.compile(r"-+")


def _slugify(name: str) -> str:
    s = name.lower().strip().replace(" ", "-")
    s = _SLUG_INVALID_RE.sub("-", s)
    s = _SLUG_DASH_RE.sub("-", s).strip("-")
    s = s[:60]
    return s or "workspace"


async def _make_unique_slug(db: AsyncSession, base: str) -> str:
    """slug 충돌 시 6자 랜덤 접미사로 재시도. 최대 5회."""
    for attempt in range(5):
        candidate = base if attempt == 0 else f"{base}-{secrets.token_hex(3)}"
        exists = await db.scalar(
            select(Workspace.id).where(Workspace.slug == candidate).limit(1)
        )
        if exists is None:
            return candidate
    raise RuntimeError("Failed to generate unique slug after 5 attempts")


# ============================================================
# 권한 검증 의존성 alias (가독성)
# ============================================================

WorkspaceMemberCtx = Annotated[
    tuple[AuthenticatedUser, WorkspaceRole],
    Depends(require_workspace_role(WorkspaceRole.viewer)),
]
WorkspaceAdminCtx = Annotated[
    tuple[AuthenticatedUser, WorkspaceRole],
    Depends(require_workspace_role(WorkspaceRole.admin)),
]
WorkspaceOwnerCtx = Annotated[
    tuple[AuthenticatedUser, WorkspaceRole],
    Depends(require_workspace_role(WorkspaceRole.owner)),
]


# ============================================================
# Endpoints
# ============================================================


@router.get("", response_model=list[WorkspaceResponse])
async def list_workspaces(user: CurrentUser, db: DbSession) -> list[WorkspaceResponse]:
    """호출자가 멤버인 모든 워크스페이스 + 본인의 역할."""
    stmt = (
        select(Workspace, WorkspaceMember.role)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    return [
        WorkspaceResponse.model_validate(ws).model_copy(update={"role": role})
        for ws, role in rows
    ]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    user: CurrentUser,
    db: DbSession,
) -> WorkspaceResponse:
    """워크스페이스 생성. 트리거가 자동으로 호출자를 owner 멤버로 추가."""
    base_slug = _slugify(payload.name)
    slug = await _make_unique_slug(db, base_slug)

    workspace = Workspace(
        name=payload.name,
        slug=slug,
        primary_language=payload.primary_language,
        timezone=payload.timezone,
        owner_id=user.id,
    )
    db.add(workspace)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workspace slug already exists",
        ) from exc

    await db.refresh(workspace)
    return WorkspaceResponse.model_validate(workspace).model_copy(
        update={"role": WorkspaceRole.owner}
    )


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    ctx: WorkspaceMemberCtx,
    db: DbSession,
) -> WorkspaceResponse:
    _user, role = ctx
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        # require_workspace_role이 이미 멤버십을 확인했으므로 일반적으로 도달 안 함.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return WorkspaceResponse.model_validate(workspace).model_copy(update={"role": role})


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    payload: WorkspaceUpdate,
    ctx: WorkspaceAdminCtx,
    db: DbSession,
) -> WorkspaceResponse:
    _user, role = ctx
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(workspace, key, value)

    await db.commit()
    await db.refresh(workspace)
    return WorkspaceResponse.model_validate(workspace).model_copy(update={"role": role})


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_workspace(
    workspace_id: UUID,
    ctx: WorkspaceOwnerCtx,
    db: DbSession,
) -> None:
    """워크스페이스 삭제.

    TODO Phase 2: deletion_grace_queue를 통한 7일 grace 처리로 전환.
    현재는 즉시 hard delete (CASCADE로 workspace_members 등 함께 삭제).
    """
    _ = ctx  # owner 검증만 필요, 본문에서는 미사용.
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    await db.delete(workspace)
    await db.commit()
