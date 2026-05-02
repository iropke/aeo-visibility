"""FastAPI 의존성: 인증, DB, 권한 검사.

라우터에서 ``Depends(get_current_user)`` 형태로 사용.
"""
from __future__ import annotations

from typing import Annotated, Callable
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import (
    AuthenticatedUser,
    InvalidJWTError,
    JWTSecretMissingError,
    decode_supabase_jwt,
)
from app.auth.permissions import assert_workspace_role, get_user_role
from app.models.database import get_db
from app.models.workspace import WorkspaceRole


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> AuthenticatedUser:
    """``Authorization: Bearer <jwt>`` 헤더에서 사용자 추출.

    검증 실패 시 401, secret 미설정 시 500.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return decode_supabase_jwt(token)
    except JWTSecretMissingError as exc:
        # 서버 설정 문제 — 500으로 반환.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except InvalidJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


def require_workspace_role(required: WorkspaceRole) -> Callable:
    """라우터 의존성 팩토리: 경로 파라미터 ``workspace_id``의 멤버십과 역할을 검증.

    사용 예::

        @router.get("/workspaces/{workspace_id}/members")
        async def list_members(
            workspace_id: UUID,
            current = Depends(require_workspace_role(WorkspaceRole.member)),
        ):
            ...
    """
    async def _dependency(
        workspace_id: Annotated[UUID, Path()],
        user: CurrentUser,
        db: DbSession,
    ) -> tuple[AuthenticatedUser, WorkspaceRole]:
        try:
            role = await assert_workspace_role(db, user.id, workspace_id, required)
        except PermissionError as exc:
            # 멤버가 아닌 경우와 권한 부족을 동일하게 403 처리 (워크스페이스 존재 노출 방지).
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc
        return user, role

    return _dependency


async def get_optional_workspace_role(
    workspace_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> WorkspaceRole | None:
    """역할이 있으면 반환, 멤버 아니면 None (강제 안 함)."""
    return await get_user_role(db, user.id, workspace_id)
