"""monthly_usage 카운터 — Custom 분석 차감 + 잔여 조회.

분석 라우터(``app.routers.analyses``)와 매월 cron(Phase 2 internal 라우터)이 사용.

차감 우선순위 (SPEC §5 + 메모리 funding source 분리):
    pro_pack → basic_pack → base → payg

각 funding source 별 월간 quota:
    - pro_pack:   active subscription_addons(custom_pack_pro) × 20  (Phase 2 = 0)
    - basic_pack: active subscription_addons(custom_pack_basic) × 5 (Phase 2 = 0)
    - base:       workspace.plan.custom_analyses_per_month
    - payg:       무한 (단발 결제) — 사용자가 명시적으로 ``allow_payg=True`` 일 때만 선택
                  Phase 1은 결제 미연동이라 라우터에서 PAYG는 ``enable=False``.

설계 원칙:
    - quota 결정과 차감은 같은 트랜잭션에서 수행 (race condition 방지를 위해 row lock).
    - ``-1`` quota = 무제한 (enterprise plan 패턴 일관).
    - DB CHECK ≥ 0이 보장하지만 quota 검사는 라우터 레벨에서 명시.
    - addon 합산 로직은 Phase 2에서 ``_get_addon_quotas`` 한 곳만 교체하면 끝.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_result import AnalysisFundingSource
from app.models.monthly_usage import MonthlyUsage
from app.models.plan import Plan
from app.models.workspace import Workspace


# ─── public helpers ──────────────────────────────────────────────


def current_year_month(now: datetime | None = None) -> str:
    """``YYYY-MM`` 포맷 — monthly_usage.year_month 컬럼과 동일."""
    ts = now or datetime.now(timezone.utc)
    return f"{ts.year:04d}-{ts.month:02d}"


@dataclass(frozen=True)
class QuotaSnapshot:
    """현재 월의 funding source 별 quota / used / remaining 스냅샷.

    ``-1`` quota는 무제한 (enterprise). ``remaining`` 도 ``-1`` 로 표기.
    """
    year_month: str
    pro_pack_quota: int
    pro_pack_used: int
    basic_pack_quota: int
    basic_pack_used: int
    base_quota: int
    base_used: int
    payg_used: int

    def remaining(self, source: AnalysisFundingSource) -> int:
        """``-1`` 무제한, 0 이상은 잔여 횟수. payg는 항상 ``-1`` (단발 결제)."""
        if source is AnalysisFundingSource.pro_pack:
            return _remaining(self.pro_pack_quota, self.pro_pack_used)
        if source is AnalysisFundingSource.basic_pack:
            return _remaining(self.basic_pack_quota, self.basic_pack_used)
        if source is AnalysisFundingSource.base:
            return _remaining(self.base_quota, self.base_used)
        if source is AnalysisFundingSource.payg:
            return -1  # 단발 결제 — quota 개념 없음.
        # auto: 매월 cron 내부 차감 (사용자 라우터에서는 도달 ❌).
        raise ValueError(f"remaining() not defined for source={source.value}")


def _remaining(quota: int, used: int) -> int:
    if quota == -1:
        return -1
    return max(quota - used, 0)


# ─── DB ops ──────────────────────────────────────────────────────


async def upsert_and_lock_usage_row(
    db: AsyncSession,
    workspace_id: UUID,
    year_month: str,
) -> MonthlyUsage:
    """월간 usage row를 upsert(없으면 zero row INSERT)한 뒤 row lock 획득.

    ``ON CONFLICT DO NOTHING`` 으로 INSERT 시도 → ``SELECT ... FOR UPDATE`` 로
    동시 차감 race 방지. 호출자는 같은 트랜잭션 내에서 차감 + analysis_result
    INSERT 후 commit 해야 락이 풀림.
    """
    stmt = pg_insert(MonthlyUsage).values(
        workspace_id=workspace_id,
        year_month=year_month,
    ).on_conflict_do_nothing(
        index_elements=["workspace_id", "year_month"],
    )
    await db.execute(stmt)

    locked = await db.scalar(
        select(MonthlyUsage)
        .where(
            MonthlyUsage.workspace_id == workspace_id,
            MonthlyUsage.year_month == year_month,
        )
        .with_for_update()
    )
    assert locked is not None, "monthly_usage upsert+lock should always return a row"
    return locked


async def _get_workspace_plan(db: AsyncSession, workspace_id: UUID) -> Plan:
    plan = await db.scalar(
        select(Plan)
        .join(Workspace, Workspace.plan_id == Plan.id)
        .where(Workspace.id == workspace_id)
    )
    if plan is None:
        raise ValueError(f"No plan found for workspace_id={workspace_id}")
    return plan


async def _get_addon_quotas(
    db: AsyncSession, workspace_id: UUID, year_month: str
) -> tuple[int, int]:
    """active subscription_addons 합산 → (pro_pack_quota, basic_pack_quota).

    Phase 1: subscription_addons 테이블 미존재 → (0, 0). Phase 2 결제 시점에
    addon 모델 도입 후 이 함수만 교체.
    """
    _ = (db, workspace_id, year_month)
    return (0, 0)


async def get_quota_snapshot(
    db: AsyncSession,
    workspace_id: UUID,
    *,
    usage_row: MonthlyUsage | None = None,
    year_month: str | None = None,
) -> QuotaSnapshot:
    """현재 월 quota / used 스냅샷. ``usage_row`` 미제공 시 (lock 없이) 조회 INSERT.

    GET 잔여 조회용 — 차감 흐름은 ``upsert_and_lock_usage_row`` 직접 호출 후
    이 함수에 row를 주입.
    """
    ym = year_month or current_year_month()
    if usage_row is None:
        usage_row = await upsert_and_lock_usage_row(db, workspace_id, ym)
    plan = await _get_workspace_plan(db, workspace_id)
    pro_q, basic_q = await _get_addon_quotas(db, workspace_id, ym)
    return QuotaSnapshot(
        year_month=ym,
        pro_pack_quota=pro_q,
        pro_pack_used=usage_row.pro_pack_analyses_used,
        basic_pack_quota=basic_q,
        basic_pack_used=usage_row.basic_pack_analyses_used,
        base_quota=plan.custom_analyses_per_month,
        base_used=usage_row.base_analyses_used,
        payg_used=usage_row.payg_analyses_used,
    )


# ─── funding source selection + decrement ───────────────────────


# 사용자 트리거(custom) 차감 우선순위. 'auto' 는 cron 전용 (라우터에서 미사용).
_PRIORITY: tuple[AnalysisFundingSource, ...] = (
    AnalysisFundingSource.pro_pack,
    AnalysisFundingSource.basic_pack,
    AnalysisFundingSource.base,
)


class InsufficientQuotaError(Exception):
    """모든 funding source quota 소진. 라우터에서 402 변환."""

    def __init__(self, snapshot: QuotaSnapshot) -> None:
        super().__init__("Custom analysis quota exhausted for this month")
        self.snapshot = snapshot


def select_funding_source(
    snapshot: QuotaSnapshot,
    *,
    allow_payg: bool = False,
) -> AnalysisFundingSource:
    """우선순위 순으로 잔여 quota 있는 source 선택. 모두 0이고 payg 허용이면 payg.

    Raises:
        InsufficientQuotaError: 모든 quota 소진 + payg 비허용.
    """
    for source in _PRIORITY:
        if snapshot.remaining(source) != 0:  # -1 (무제한) 또는 양수.
            return source
    if allow_payg:
        return AnalysisFundingSource.payg
    raise InsufficientQuotaError(snapshot)


def increment_used(usage_row: MonthlyUsage, source: AnalysisFundingSource) -> None:
    """해당 funding source 카운터 +1 (in-place). 호출자가 commit 해야 영구화.

    DB CHECK ≥ 0 가 음수 차단, INT 범위 내에서 자유 증가.
    """
    if source is AnalysisFundingSource.pro_pack:
        usage_row.pro_pack_analyses_used = usage_row.pro_pack_analyses_used + 1
    elif source is AnalysisFundingSource.basic_pack:
        usage_row.basic_pack_analyses_used = usage_row.basic_pack_analyses_used + 1
    elif source is AnalysisFundingSource.base:
        usage_row.base_analyses_used = usage_row.base_analyses_used + 1
    elif source is AnalysisFundingSource.payg:
        usage_row.payg_analyses_used = usage_row.payg_analyses_used + 1
    else:
        raise ValueError(f"increment_used() not defined for source={source.value}")
