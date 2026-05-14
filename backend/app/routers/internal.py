"""Internal cron endpoints — pg_cron 호출 전용, HMAC 검증.

엔드포인트:
    POST /api/internal/cron/monthly-analysis        매월 1일 자동 분석 (Phase 1 stub)
    POST /api/internal/cron/trial-expiry-sequence   Day 7 / 30 / 90 메일 시퀀스

검증:
    헤더 ``X-Cron-Timestamp`` (epoch seconds) + ``X-Cron-Signature`` (lowercase hex).
    signature = HMAC-SHA256(secret, timestamp || body_text).
    timestamp 가 NOW() ± window 외 → 401 (replay 차단).

호출자:
    019_pg_cron_setup 의 ``internal.cron_post(...)`` PL/pgSQL 헬퍼.
    백엔드 ``internal_cron_hmac_secret`` ↔ postgres ``app.cron_hmac_secret`` 동일.

Phase 1 스코프:
    - monthly-analysis: stub (eligible 워크스페이스 카운트만 반환).
    - trial-expiry-sequence: 실 발송 (G7/G8 helper 호출).

Phase 2/3:
    - monthly-analysis 본문에 자동 analysis_result row INSERT + analysis_task 호출.
    - grace_processor cron (deletion_grace_queue) 추가.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy import select

from app.config import get_settings
from app.deps import DbSession
from app.models.subscription import Subscription, SubscriptionStatus
from app.services.email_service import (
    TRIAL_EXPIRY_DAYS,
    send_trial_expiry_email,
)


log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/internal", tags=["internal"])


# ── HMAC 검증 ────────────────────────────────────────────────────


async def _verify_cron_signature(
    request: Request,
    x_cron_timestamp: Annotated[str | None, Header()] = None,
    x_cron_signature: Annotated[str | None, Header()] = None,
) -> None:
    """X-Cron-* 헤더 + body 기반 HMAC-SHA256 검증.

    실패 분기:
        500 — 서버 시크릿 미설정 (의도적: 실수 활성화 차단)
        401 — 헤더 누락 / 타임스탬프 형식 / 윈도우 외 / 서명 불일치
    """
    settings = get_settings()
    secret = settings.internal_cron_hmac_secret
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="internal_cron_hmac_secret not configured",
        )
    if not x_cron_timestamp or not x_cron_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing X-Cron-Timestamp or X-Cron-Signature header",
        )
    try:
        ts = int(x_cron_timestamp)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid X-Cron-Timestamp format",
        ) from exc

    window = settings.internal_cron_replay_window_seconds
    if abs(int(time.time()) - ts) > window:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"X-Cron-Timestamp out of replay window ({window}s)",
        )

    body_bytes = await request.body()
    # body 가 비어 있으면 pg_net 이 '{}' 또는 '' 로 보냄 — Postgres 측 hmac() 입력과
    # 일치하도록 빈 바이트는 빈 문자열로 처리.
    body_text = body_bytes.decode("utf-8") if body_bytes else ""
    msg = (x_cron_timestamp + body_text).encode("utf-8")
    expected_hex = hmac.new(
        secret.encode("utf-8"), msg, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected_hex, x_cron_signature.lower()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid X-Cron-Signature",
        )


# ── endpoints ────────────────────────────────────────────────────


@router.post("/cron/monthly-analysis")
async def monthly_analysis(
    request: Request,
    db: DbSession,
    x_cron_timestamp: Annotated[str | None, Header()] = None,
    x_cron_signature: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """매월 1일 자동 분석 (Phase 1 stub).

    Phase 1: eligible 워크스페이스 (trial / active) 카운트만 집계 + log.
    Phase 3: 각 워크스페이스 own site 별 trigger_type='auto' INSERT + analysis_task 큐.
    """
    await _verify_cron_signature(request, x_cron_timestamp, x_cron_signature)

    rows = (
        await db.execute(
            select(Subscription.workspace_id).where(
                Subscription.status.in_(
                    (SubscriptionStatus.trial, SubscriptionStatus.active)
                )
            )
        )
    ).all()
    workspace_ids = [r[0] for r in rows]

    log.info(
        "cron monthly-analysis: %s eligible workspaces (Phase 1 stub)",
        len(workspace_ids),
    )
    return {
        "status": "stub",
        "eligible_workspaces": len(workspace_ids),
        "message": "Phase 1 stub — auto-analysis triggering arrives in Phase 3",
    }


@router.post("/cron/trial-expiry-sequence")
async def trial_expiry_sequence(
    request: Request,
    db: DbSession,
    x_cron_timestamp: Annotated[str | None, Header()] = None,
    x_cron_signature: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Day 7 / 30 / 90 트라이얼 만료 메일 시퀀스 일괄 발송 (G8 helper 호출).

    멱등성: cron 이 매일 09:00 UTC 1회 실행 → 각 워크스페이스 × day 조합당 1회만
    매칭 (trial_ends_at + day 가 today UTC 인 단일 24시간 윈도우).

    매칭 조건:
        subscriptions.status = 'trial' AND
        trial_ends_at >= today_start - day  AND
        trial_ends_at <  today_end   - day

    실 발송은 ``email_service.send_trial_expiry_email`` (per-workspace owner only).
    """
    await _verify_cron_signature(request, x_cron_timestamp, x_cron_signature)

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    summary: dict[str, Any] = {
        "days": {},
        "total_sent": 0,
        "total_skipped": 0,
        "total_matched": 0,
    }

    for day in TRIAL_EXPIRY_DAYS:
        target_lo = today_start - timedelta(days=day)
        target_hi = today_end - timedelta(days=day)

        rows = (
            await db.execute(
                select(Subscription.workspace_id).where(
                    Subscription.status == SubscriptionStatus.trial,
                    Subscription.trial_ends_at.isnot(None),
                    Subscription.trial_ends_at >= target_lo,
                    Subscription.trial_ends_at < target_hi,
                )
            )
        ).all()
        workspace_ids = [r[0] for r in rows]

        sent = 0
        skipped = 0
        for ws_id in workspace_ids:
            try:
                result = await send_trial_expiry_email(
                    db, workspace_id=ws_id, day=day,
                )
                sent += int(result.get("sent", 0))
                skipped += int(result.get("skipped", 0))
            except Exception:  # noqa: BLE001
                log.exception(
                    "trial-expiry day=%s ws=%s send raised", day, ws_id,
                )
                skipped += 1

        summary["days"][str(day)] = {
            "matched": len(workspace_ids),
            "sent": sent,
            "skipped": skipped,
        }
        summary["total_sent"] += sent
        summary["total_skipped"] += skipped
        summary["total_matched"] += len(workspace_ids)

    log.info(
        "cron trial-expiry: matched=%s sent=%s skipped=%s",
        summary["total_matched"],
        summary["total_sent"],
        summary["total_skipped"],
    )
    return summary
