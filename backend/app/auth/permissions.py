"""워크스페이스 권한 / 쓰기 가능 상태 검증 헬퍼.

백엔드는 service_role 또는 직접 DB 연결을 사용해 RLS를 우회하므로,
권한 검증은 Python 레벨에서 명시적으로 수행한다.

쓰기 가능 상태(트라이얼 만료/해지 게이팅)는 ``assert_workspace_writable`` 사용.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription, SubscriptionStatus
from app.models.workspace import WorkspaceMember, WorkspaceRole


class WorkspaceReadOnlyError(Exception):
    """워크스페이스가 읽기 전용 상태일 때 (트라이얼 만료, 해지 등).

    라우터 의존성에서 ``HTTPException(402 Payment Required)``로 변환.
    """


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


async def assert_workspace_writable(
    db: AsyncSession,
    workspace_id: UUID,
) -> None:
    """워크스페이스가 쓰기 가능 상태인지 검증. 아니면 ``WorkspaceReadOnlyError``.

    SPEC §4-3 / §8 정합:

    쓰기 가능 (writable):
        - status='trial' AND trial_ends_at >= NOW()  (활성 트라이얼)
        - status='active' (정상 결제)
        - status='past_due' (결제 실패 — 1/3/7일 리트라이 grace 동안 쓰기 허용)
        - status='paused' (일시 정지 — 사용자 요청, 결제만 정지)

    읽기 전용 (read-only):
        - status='trial' AND trial_ends_at < NOW()  (트라이얼 만료)
        - status='canceled' (해지 — 1년 grace 기간 데이터만 열람)

    라우터 의존성에서 호출 → ``HTTPException(402 Payment Required)``로 변환.
    Stripe Checkout / Customer Portal 등 결제 흐름은 게이팅에서 제외 (별도 라우터).
    """
    sub = await db.scalar(
        select(Subscription)
        .where(Subscription.workspace_id == workspace_id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    if sub is None:
        # 009의 트리거가 자동 INSERT하므로 일반적으로 도달 ❌.
        # 도달했다면 데이터 정합성 이슈 — 안전하게 read-only로 처리.
        raise WorkspaceReadOnlyError("No subscription record found for workspace")

    if sub.status == SubscriptionStatus.trial:
        if sub.trial_ends_at is not None and sub.trial_ends_at < datetime.now(timezone.utc):
            raise WorkspaceReadOnlyError(
                f"Trial expired at {sub.trial_ends_at.isoformat()}; upgrade to continue"
            )
        return

    if sub.status == SubscriptionStatus.canceled:
        raise WorkspaceReadOnlyError(
            "Workspace subscription is canceled; reactivate to continue"
        )

    # active / past_due / paused: writable.
    return
