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
from app.auth.permissions import (
    REQUIRED_ROLE_FOR_ACTION,
    WorkspaceAction,
    WorkspaceReadOnlyError,
    assert_workspace_action,
    assert_workspace_role,
    assert_workspace_writable,
    get_user_role,
)
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


def require_writable_workspace_role(required: WorkspaceRole) -> Callable:
    """역할 검증 + 쓰기 가능 상태 (트라이얼 만료/해지) 검사를 결합한 의존성 팩토리.

    role 부족 → 403, 읽기 전용 상태 → 402 Payment Required.
    쓰기 엔드포인트 (POST / PATCH / DELETE)에 사용. 읽기는 ``require_workspace_role`` 사용.
    Stripe Checkout / Customer Portal 흐름에는 적용하지 않음 (만료 후에도 업그레이드 가능해야 함).
    """
    async def _dependency(
        workspace_id: Annotated[UUID, Path()],
        user: CurrentUser,
        db: DbSession,
    ) -> tuple[AuthenticatedUser, WorkspaceRole]:
        try:
            role = await assert_workspace_role(db, user.id, workspace_id, required)
        except PermissionError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc
        try:
            await assert_workspace_writable(db, workspace_id)
        except WorkspaceReadOnlyError as exc:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
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


def require_action(action: WorkspaceAction, *, writable: bool = True) -> Callable:
    """행위 단위 권한 의존성 팩토리.

    ``WorkspaceAction`` enum + 사전 매핑(``REQUIRED_ROLE_FOR_ACTION``) 기반 가드.
    ``writable=True`` 면 트라이얼 만료/해지 시 402 차단 추가.

    예:
        Depends(require_action(WorkspaceAction.analysis_trigger))  # member+ & writable
        Depends(require_action(WorkspaceAction.analysis_view, writable=False))  # viewer+
    """
    # 매핑 누락은 빌드 타임에 KeyError로 검출.
    _ = REQUIRED_ROLE_FOR_ACTION[action]

    async def _dependency(
        workspace_id: Annotated[UUID, Path()],
        user: CurrentUser,
        db: DbSession,
    ) -> tuple[AuthenticatedUser, WorkspaceRole]:
        try:
            role = await assert_workspace_action(db, user.id, workspace_id, action)
        except PermissionError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            ) from exc
        if writable:
            try:
                await assert_workspace_writable(db, workspace_id)
            except WorkspaceReadOnlyError as exc:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=str(exc),
                ) from exc
        return user, role

    return _dependency
