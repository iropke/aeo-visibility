"""워크스페이스 권한 검증 헬퍼.

백엔드는 service_role 또는 직접 DB 연결을 사용해 RLS를 우회하므로,
권한 검증은 Python 레벨에서 명시적으로 수행한다.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import WorkspaceMember, WorkspaceRole


# 역할 우선순위 (높은 권한이 큰 값) — 'X 이상' 검사용.
_ROLE_RANK: dict[WorkspaceRole, int] = {
    WorkspaceRole.viewer: 1,
    WorkspaceRole.member: 2,
    WorkspaceRole.admin: 3,
    WorkspaceRole.owner: 4,
}


async def get_user_role(
    db: AsyncSession,
    user_id: UUID,
    workspace_id: UUID,
) -> WorkspaceRole | None:
    """주어진 사용자의 워크스페이스 역할 조회. 멤버가 아니면 None."""
    stmt = select(WorkspaceMember.role).where(
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.workspace_id == workspace_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def has_required_role(
    actual: WorkspaceRole | None,
    required: WorkspaceRole,
) -> bool:
    """``actual``이 ``required`` 이상의 권한인지 검사."""
    if actual is None:
        return False
    return _ROLE_RANK[actual] >= _ROLE_RANK[required]


async def assert_workspace_role(
    db: AsyncSession,
    user_id: UUID,
    workspace_id: UUID,
    required: WorkspaceRole,
) -> WorkspaceRole:
    """권한 부족 시 PermissionError 발생.

    라우터 의존성에서 호출 → ``HTTPException(403)``로 변환.
    """
    role = await get_user_role(db, user_id, workspace_id)
    if not has_required_role(role, required):
        raise PermissionError(
            f"Required role '{required.value}' or higher; user has '{role.value if role else 'none'}'"
        )
    return role  # type: ignore[return-value]
