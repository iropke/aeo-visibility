"""워크스페이스 멤버 라우터.

엔드포인트:
    GET    /api/workspaces/{workspace_id}/members            목록 (멤버)
    PATCH  /api/workspaces/{workspace_id}/members/{user_id}  역할 변경 (owner)
    DELETE /api/workspaces/{workspace_id}/members/{user_id}  제거 (owner/admin) 또는 본인 떠나기

신규 멤버 INSERT는 ``workspace_invitations`` 흐름을 통해서만 — Phase 2.
"""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.auth.jwt import AuthenticatedUser
from app.deps import (
    CurrentUser,
    DbSession,
    require_workspace_role,
)
from app.models.profile import Profile
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.workspace import MemberResponse, MemberRoleUpdate

router = APIRouter(prefix="/api/workspaces", tags=["members"])


WorkspaceMemberCtx = Annotated[
    tuple[AuthenticatedUser, WorkspaceRole],
    Depends(require_workspace_role(WorkspaceRole.viewer)),
]
WorkspaceOwnerCtx = Annotated[
    tuple[AuthenticatedUser, WorkspaceRole],
    Depends(require_workspace_role(WorkspaceRole.owner)),
]


@router.get("/{workspace_id}/members", response_model=list[MemberResponse])
async def list_members(
    workspace_id: UUID,
    ctx: WorkspaceMemberCtx,
    db: DbSession,
) -> list[MemberResponse]:
    _ = ctx  # 멤버십 검증만 필요.
    stmt = (
        select(WorkspaceMember, Profile.display_name)
        .join(Profile, Profile.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .order_by(WorkspaceMember.joined_at.asc())
    )
    rows = (await db.execute(stmt)).all()
    return [
        MemberResponse.model_validate(member).model_copy(update={"display_name": display_name})
        for member, display_name in rows
    ]


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=MemberResponse,
)
async def update_member_role(
    workspace_id: UUID,
    user_id: UUID,
    payload: MemberRoleUpdate,
    ctx: WorkspaceOwnerCtx,
    db: DbSession,
) -> MemberResponse:
    """역할 변경. owner만 호출 가능.

    제약:
    - 자기 자신을 owner→admin 등으로 강등하려면 별도 ownership-transfer 흐름 사용 (Phase 2).
      현재 라우터는 단순 PATCH만 — 다른 멤버의 역할 변경에 사용.
    """
    actor, _ = ctx

    if user_id == actor.id and payload.role != WorkspaceRole.owner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Owner cannot self-demote; use ownership transfer flow",
        )

    member = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    member.role = payload.role
    await db.commit()
    await db.refresh(member)

    profile = await db.get(Profile, user_id)
    return MemberResponse.model_validate(member).model_copy(
        update={"display_name": profile.display_name if profile else None},
    )


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def remove_member(
    workspace_id: UUID,
    user_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    """멤버 제거.

    허용 케이스:
    - 본인이 워크스페이스 떠나기 (단, owner는 안 됨 — 이양 후 가능)
    - owner/admin이 다른 멤버 제거 (단, owner를 admin이 제거 ❌, owner를 owner가 제거 ❌)
    """
    is_self = user_id == user.id

    # actor 자신의 역할 조회.
    from app.auth.permissions import get_user_role

    actor_role = await get_user_role(db, user.id, workspace_id)
    if actor_role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")

    # 대상 멤버 조회.
    target = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    if is_self:
        if target.role == WorkspaceRole.owner:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Owner must transfer ownership before leaving",
            )
        # 본인 떠나기 — 항상 허용.
    else:
        # 타인 제거 — owner/admin만, owner 대상 ❌
        if actor_role not in (WorkspaceRole.owner, WorkspaceRole.admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owner or admin can remove other members",
            )
        if target.role == WorkspaceRole.owner:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the workspace owner",
            )

    await db.delete(target)
    await db.commit()
