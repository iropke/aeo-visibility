"""Contact 폼 라우터 — public POST.

엔드포인트:
    POST /api/contact   — 폼 응답 저장 + admin 알림 메일 (인증 ❌)

어뷰징 방지 (SPEC §4-5 정합):
    1. honeypot — Pydantic ``ContactCreate.website`` 가 비어있어야 통과.
       비어있지 않으면 200 OK 로 위장 응답 + DB 저장 ❌ (bot 에게 신호 ❌).
    2. IP rate limit — 동일 IP sha256 hash 키로 1분 3회 (services/rate_limit).
       초과 시 429 Too Many Requests.
    3. message length — Pydantic 5000자 / name 200자 / company 200자 제약.

호출 흐름:
    1. honeypot 통과? → 아니면 fake-success 200 (조용히 drop).
    2. rate limit 통과? → 아니면 429.
    3. DB INSERT — service_role bypass RLS (백엔드 service_role 사용).
    4. BackgroundTasks 로 admin 알림 메일 발송 (실패 swallow).
    5. 200 OK ContactResponse.

Phase 2 admin 패널 청크에서 GET/PATCH endpoint 추가 예정 (status 변경 등).
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.contact_submission import ContactSubmission
from app.models.database import get_db
from app.schemas.contact import ContactCreate, ContactResponse
from app.services.email_service import send_contact_notification
from app.services.rate_limit import check_and_record, hash_ip

router = APIRouter(prefix="/api/contact", tags=["contact"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

log = logging.getLogger(__name__)


def _client_ip(request: Request) -> str:
    """X-Forwarded-For 우선 + client.host 폴백.

    프록시(Cloudflare/Vercel 등) 뒤일 때 X-Forwarded-For 의 첫 IP 가 원본 클라이언트.
    개발 환경(직접 연결)에서는 client.host = 127.0.0.1.
    """
    fwd = request.headers.get("X-Forwarded-For", "").strip()
    if fwd:
        first = fwd.split(",", 1)[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


@router.post("", response_model=ContactResponse, status_code=status.HTTP_200_OK)
async def create_contact_submission(
    payload: ContactCreate,
    request: Request,
    background: BackgroundTasks,
    db: DbSession,
) -> ContactResponse:
    """공개 Contact 폼 제출. 익명/비인증 OK."""
    settings = get_settings()

    # 1. honeypot — bot 이 hidden field 채우면 fake-success 응답.
    #    DB INSERT/메일 발송 ❌ — bot 에게 polished error 노출 ❌.
    if payload.website:
        log.info(
            "contact: honeypot triggered ip=%s topic=%s",
            _client_ip(request), payload.topic.value,
        )
        return ContactResponse()

    # 2. rate limit — 동일 IP 1분 3회.
    ip = _client_ip(request)
    ip_hash = hash_ip(ip, salt=settings.contact_ip_hash_salt)
    allowed = await check_and_record(ip_hash)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )

    # 3. DB INSERT.
    user_agent = (request.headers.get("User-Agent") or "")[:500]
    referrer = (request.headers.get("Referer") or "")[:500] or None

    submission = ContactSubmission(
        name=payload.name,
        email=payload.email,
        company=payload.company,
        topic=payload.topic,
        message=payload.message,
        locale=payload.locale,
        referrer_url=referrer,
        ip_hash=ip_hash,
        user_agent=user_agent or None,
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    log.info(
        "contact: submission saved id=%s topic=%s locale=%s",
        submission.id, submission.topic.value, submission.locale,
    )

    # 4. admin 알림 메일 (BG, fire-and-forget).
    background.add_task(
        _send_contact_notification_safe,
        submission_payload={
            "name": submission.name,
            "email": submission.email,
            "company": submission.company,
            "topic": submission.topic,
            "message": submission.message,
            "locale": submission.locale,
            "referrer_url": submission.referrer_url,
        },
        submission_id=submission.id,
    )

    return ContactResponse()


async def _send_contact_notification_safe(*, submission_payload: dict, submission_id) -> None:
    """BackgroundTasks 안전 wrapper — 어떤 예외도 swallow 한다."""
    try:
        await send_contact_notification(
            submission=submission_payload, submission_id=submission_id,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "contact: notification send failed id=%s err=%s",
            submission_id, exc,
        )
