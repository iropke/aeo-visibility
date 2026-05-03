"""트랜잭셔널 이메일 서비스 (SPEC §17, Resend).

Phase 1 G7-email-core (2026-05-03):
    - 분석 완료 메일 (``analysis_complete``) — workspace owner+admin+analyzed_by.
    - 수신자별 ``profiles.preferred_language`` 기준 언어 분기 (en/ko/es).
    - 템플릿: ``backend/app/templates/{trigger}/{lang}.html`` (Jinja2 autoescape on).
    - G6 ``insights.summary[lang]`` + ``improvements.items`` (상위 5) 직접 임베드.
    - ``resend_api_key`` 빈 값 → silent skip (개발 환경 안전).
    - Resend API 호출 실패 → swallow + log (분석 결과는 이미 DB 저장됨, best-effort).

Phase 1 G8-email-trial-sequence (2026-05-03):
    - 트라이얼 만료 시퀀스 (``trial_expiry_day{7,30,90}``) — workspace owner only.
    - 본문은 SPEC §4-3 시퀀스 표 정합 — Day 7=30%, Day 30=50%, Day 90=50%+demo.
    - 쿠폰 코드 inject 는 Phase 2 쿠폰 청크에서 (현재는 할인 % + Pricing CTA 만).
    - cron 스케줄링은 별도 청크 (017_pg_cron_setup) — 본 모듈은 helper 만 제공.

Phase 2 (Magic Link / 017_pg_cron / 결제 청크):
    - Magic Link (Supabase Auth Hook 또는 직접 발송).
    - 결제 영수증 / 결제 실패 / 워크스페이스 초대.

설계 메모:
    - ``auth.users.email`` 은 schema=auth 에 있어 ORM 매핑 ❌ → ``text()`` raw SQL 한 줄.
      (postgres pooler 사용자는 auth 스키마 접근 가능, RLS 적용 ❌.)
    - 발송 호출은 항상 ``async`` — Resend SDK 가 동기지만 ``asyncio.to_thread`` 로 감쌈.
      하나의 메일 실패가 다른 수신자 발송 막지 않도록 per-recipient try/except.
    - i18n 사전 키 lookup ❌ — 템플릿 자체가 lang 별 분리. Jinja2 ``{{ var }}`` 가
      G6 multilingual JSONB 의 ``[lang]`` 인덱스 결과만 받음.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID

import resend
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.analysis_result import AnalysisResult
from app.models.profile import Profile
from app.models.site import Site
from app.models.workspace import WorkspaceMember, WorkspaceRole


log = logging.getLogger(__name__)


# ─── 상수 ─────────────────────────────────────────────────────────────

TEMPLATES_DIR: Path = Path(__file__).parent.parent / "templates"

# i18n 지원 언어 — profiles.preferred_language CHECK 와 동일.
SUPPORTED_LANGS: tuple[str, ...] = ("en", "ko", "es")
SUPPORTED_LANG_SET: frozenset[str] = frozenset(SUPPORTED_LANGS)
DEFAULT_LANG: str = "en"

# 발송 alias — SPEC §17-1 (no-reply@ahxov.com), 도메인 ahxov.com 확정 (2026-05-03).
FROM_ADDRESS: str = "AEO Visibility <no-reply@ahxov.com>"

# 분석 완료 메일 수신자: workspace owner + admin + analyzed_by (G7 합의).
NOTIFY_ROLES: tuple[WorkspaceRole, ...] = (
    WorkspaceRole.owner, WorkspaceRole.admin,
)

# 메일 본문 improvements 표시 상한.
IMPROVEMENTS_PREVIEW_MAX: int = 5

# Trigger key — 템플릿 디렉토리명.
TRIGGER_ANALYSIS_COMPLETE: str = "analysis_complete"

# G8 트라이얼 만료 시퀀스 — Day 7 / 30 / 90.
# SPEC §4-3 표 정합. 쿠폰 코드는 Phase 2 쿠폰 청크에서 inject.
TRIAL_EXPIRY_DAYS: tuple[int, ...] = (7, 30, 90)
TRIAL_EXPIRY_DAY_SET: frozenset[int] = frozenset(TRIAL_EXPIRY_DAYS)


def _trial_expiry_trigger(day: int) -> str:
    """day → 템플릿 디렉토리명. ``trial_expiry_day{7|30|90}``."""
    if day not in TRIAL_EXPIRY_DAY_SET:
        raise ValueError(
            f"day must be one of {sorted(TRIAL_EXPIRY_DAYS)}, got {day}"
        )
    return f"trial_expiry_day{day}"


# ─── Jinja2 환경 — lazy init ──────────────────────────────────────────

_jinja_env: Environment | None = None


def _get_jinja_env() -> Environment:
    """싱글톤 Jinja2 환경. autoescape=True (HTML 안전)."""
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    return _jinja_env


def _normalize_lang(lang: str | None) -> str:
    """SUPPORTED_LANGS 외 → DEFAULT_LANG 폴백."""
    return lang if lang in SUPPORTED_LANG_SET else DEFAULT_LANG


def render_template(trigger: str, lang: str, ctx: dict[str, Any]) -> str:
    """``templates/{trigger}/{lang}.html`` 렌더. 미지원 lang → en 폴백."""
    norm = _normalize_lang(lang)
    template = _get_jinja_env().get_template(f"{trigger}/{norm}.html")
    return template.render(**ctx)


# ─── 수신자 lookup ────────────────────────────────────────────────────

async def _resolve_recipients(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    triggered_by: UUID | None,
) -> list[dict[str, Any]]:
    """분석 완료 수신자 — owner+admin+analyzed_by 중복 제거 + email/lang 결합.

    반환: ``[{user_id, email, lang}]``.
    profiles row 없는 user_id 또는 auth.users.email 비어있는 경우는 자동 skip
    (정상 가입 흐름이면 둘 다 항상 존재).
    """
    # 1) NOTIFY_ROLES 멤버 + analyzed_by user_id 수집.
    stmt = (
        select(WorkspaceMember.user_id)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.role.in_(NOTIFY_ROLES),
        )
    )
    result = await db.execute(stmt)
    user_ids: set[UUID] = {row[0] for row in result.all()}
    if triggered_by is not None:
        user_ids.add(triggered_by)

    if not user_ids:
        return []

    # 2) profiles 에서 preferred_language 조회.
    stmt2 = (
        select(Profile.id, Profile.preferred_language)
        .where(Profile.id.in_(user_ids))
    )
    result2 = await db.execute(stmt2)
    lang_by_id: dict[UUID, str] = {row[0]: row[1] for row in result2.all()}

    # 3) auth.users.email — schema=auth 라 raw SQL.
    sql = text(
        "SELECT id, email FROM auth.users WHERE id = ANY(:ids)"
    ).bindparams()
    result3 = await db.execute(sql, {"ids": list(user_ids)})
    email_by_id: dict[UUID, str | None] = {row[0]: row[1] for row in result3.all()}

    # 4) 결합 + email 비어있는 row drop.
    recipients: list[dict[str, Any]] = []
    for uid in user_ids:
        email = email_by_id.get(uid)
        if not email:
            log.warning(
                "email_service: skip recipient user_id=%s — no auth.users.email", uid,
            )
            continue
        recipients.append({
            "user_id": uid,
            "email": email,
            "lang": _normalize_lang(lang_by_id.get(uid)),
        })
    return recipients


# ─── 발송 컨텍스트 생성 (분석 완료) ───────────────────────────────────

def _grade_color(grade: str | None) -> str:
    return {
        "A": "#22908b", "B": "#5eb6b2", "C": "#e6a817",
        "D": "#e67e22", "F": "#e74c3c",
    }.get(grade or "B", "#5eb6b2")


def _derive_grade(overall: float | None) -> str:
    if overall is None:
        return "F"
    if overall >= 90: return "A"
    if overall >= 75: return "B"
    if overall >= 60: return "C"
    if overall >= 40: return "D"
    return "F"


def _format_improvement_for_email(
    item: dict[str, Any], lang: str,
) -> dict[str, Any]:
    """improvements.items[0] 같은 dict → 메일 템플릿용 평탄 구조.

    description 은 multilingual dict — lang 인덱스 후 fallback 순서: lang → en → "".
    """
    desc_obj = item.get("description") or {}
    if isinstance(desc_obj, dict):
        description = desc_obj.get(lang) or desc_obj.get(DEFAULT_LANG) or ""
    else:
        description = str(desc_obj)
    return {
        "priority": item.get("priority") or "medium",
        "category": item.get("category") or "",
        "description": description,
        "estimated_impact": item.get("estimated_impact") or 0,
        "estimated_effort": item.get("estimated_effort") or "medium",
    }


def build_analysis_complete_context(
    *,
    analysis: AnalysisResult,
    site: Site,
    lang: str,
    frontend_url: str,
) -> dict[str, Any]:
    """분석 완료 메일 템플릿 컨텍스트 빌더.

    G6 ``insights.summary[lang]`` + ``improvements.items[].description[lang]`` 사용.
    multilingual dict 가 비어있으면 en fallback, en 도 없으면 빈 string.
    """
    insights = analysis.insights or {}
    summary_obj = insights.get("summary") or {}
    if isinstance(summary_obj, dict):
        summary = summary_obj.get(lang) or summary_obj.get(DEFAULT_LANG) or ""
    else:
        summary = str(summary_obj)

    improvements_root = analysis.improvements or {}
    items = improvements_root.get("items") if isinstance(improvements_root, dict) else None
    if not isinstance(items, list):
        items = []

    formatted_imps = [
        _format_improvement_for_email(it, lang)
        for it in items[:IMPROVEMENTS_PREVIEW_MAX]
        if isinstance(it, dict)
    ]

    overall = float(analysis.overall_score) if analysis.overall_score is not None else None
    category_scores = analysis.category_scores or {}
    grade = _derive_grade(overall)

    return {
        "site_url": site.url,
        "site_domain": site.domain,
        "overall_score": int(round(overall)) if overall is not None else 0,
        "grade": grade,
        "grade_color": _grade_color(grade),
        "summary": summary,
        "improvements": formatted_imps,
        "category_scores": {
            cat: int(round(float(score)))
            for cat, score in category_scores.items()
        },
        "result_url": (
            f"{frontend_url.rstrip('/')}/{lang}/sites/{site.id}/results/{analysis.id}"
        ),
        "lang": lang,
    }


# ─── 발송 ──────────────────────────────────────────────────────────────

def _resend_send_sync(payload: dict[str, Any]) -> None:
    """Resend SDK 동기 호출. ``asyncio.to_thread`` 로 감싸서 사용."""
    settings = get_settings()
    if not settings.resend_api_key:
        # silent skip — 개발 환경.
        return
    resend.api_key = settings.resend_api_key
    resend.Emails.send(payload)


async def _send_one(
    *, to: str, subject: str, html: str,
) -> bool:
    """단일 수신자 발송. 실패 시 swallow + log → False 반환."""
    settings = get_settings()
    if not settings.resend_api_key:
        log.info("email_service: resend_api_key empty, skip send to=%s", to)
        return False
    payload = {
        "from": FROM_ADDRESS,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    try:
        await asyncio.to_thread(_resend_send_sync, payload)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("email_service: send failed to=%s err=%s", to, exc)
        return False


# ─── 분석 완료 메일 (Phase 1 G7 메인 진입점) ──────────────────────────

# 다국어 Subject — workspace name 또는 도메인 표시.
_ANALYSIS_COMPLETE_SUBJECT: dict[str, str] = {
    "en": "AEO Visibility — Analysis complete for {domain}",
    "ko": "AEO Visibility — {domain} 분석이 완료되었습니다",
    "es": "AEO Visibility — Análisis completado para {domain}",
}


async def send_analysis_complete_email(
    db: AsyncSession,
    *,
    analysis: AnalysisResult,
    site: Site,
) -> dict[str, Any]:
    """분석 완료 메일 발송 — owner+admin+analyzed_by 별도 메일.

    반환: ``{sent: N, skipped: N, total: N, recipients: [...]}``.

    호출자는 ``BackgroundTasks`` 또는 ``asyncio.create_task`` 로 fire-and-forget
    으로 호출해도 OK — 본 함수는 예외를 swallow 함 (분석 자체 실패 처리 ❌).
    """
    settings = get_settings()
    recipients = await _resolve_recipients(
        db,
        workspace_id=analysis.workspace_id,
        triggered_by=analysis.triggered_by,
    )
    summary: dict[str, Any] = {
        "sent": 0, "skipped": 0, "total": len(recipients),
        "recipients": [],
    }
    if not recipients:
        log.info(
            "email_service: no recipients for analysis=%s ws=%s",
            analysis.id, analysis.workspace_id,
        )
        return summary

    for rcp in recipients:
        lang = rcp["lang"]
        try:
            ctx = build_analysis_complete_context(
                analysis=analysis,
                site=site,
                lang=lang,
                frontend_url=settings.frontend_url,
            )
            html = render_template(TRIGGER_ANALYSIS_COMPLETE, lang, ctx)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "email_service: render failed user=%s lang=%s err=%s",
                rcp["user_id"], lang, exc,
            )
            summary["skipped"] += 1
            summary["recipients"].append(
                {**rcp, "ok": False, "reason": "render_error"}
            )
            continue

        subject = _ANALYSIS_COMPLETE_SUBJECT[lang].format(domain=site.domain)
        ok = await _send_one(to=rcp["email"], subject=subject, html=html)
        if ok:
            summary["sent"] += 1
        else:
            summary["skipped"] += 1
        summary["recipients"].append(
            {**rcp, "ok": ok, "reason": "sent" if ok else "send_failed"}
        )
    return summary


# ─── 트라이얼 만료 시퀀스 메일 (Phase 1 G8) ──────────────────────────
#
# SPEC §4-3 표:
#   Day 7  — 즉시 전환 인센티브: 첫 달 30% 할인 (3일 한정)
#   Day 30 — 재참여 유도: 첫 달 50% 할인
#   Day 90 — 최종 제안: 첫 3개월 50% 할인 + 1:1 데모
#
# Phase 1 본문은 할인 % + 기간 명시 + Pricing CTA URL. 실제 쿠폰 코드/링크는
# Phase 2 쿠폰 청크에서 같은 템플릿에 placeholder 추가 (auto_apply 토큰 등).
#
# 수신자: workspace owner only (트라이얼 전환 결제 결정권자, G7 결정 분리).
# cron 스케줄링은 017_pg_cron_setup 청크가 trial_ends_at + day 일치 워크스페이스
# 를 select 한 뒤 본 helper 호출.

_TRIAL_EXPIRY_SUBJECT: dict[int, dict[str, str]] = {
    7: {
        "en": "AEO Visibility — Your trial ended. Get 30% off your first month",
        "ko": "AEO Visibility — 트라이얼이 종료되었어요. 첫 달 30% 할인 받기",
        "es": "AEO Visibility — Su prueba terminó. 30% de descuento en su primer mes",
    },
    30: {
        "en": "AEO Visibility — Still curious? 50% off your first month",
        "ko": "AEO Visibility — 다시 시작해보세요. 첫 달 50% 할인",
        "es": "AEO Visibility — ¿Sigue interesado? 50% de descuento en su primer mes",
    },
    90: {
        "en": "AEO Visibility — Last chance: 50% off for 3 months + free demo",
        "ko": "AEO Visibility — 마지막 기회: 첫 3개월 50% 할인 + 1:1 데모",
        "es": "AEO Visibility — Última oportunidad: 50% por 3 meses + demo gratis",
    },
}


async def _resolve_workspace_owner(
    db: AsyncSession,
    *,
    workspace_id: UUID,
) -> dict[str, Any] | None:
    """워크스페이스 owner profile + email lookup.

    반환: ``{user_id, email, lang, display_name, workspace_name}`` 또는 None.
    None 인 경우(테이블 무결성 깨짐, owner 멤버 row 없음, email 누락):
    호출자가 skip 하고 log 만 남김.
    """
    # 1) workspace + owner_id + name 조회.
    from app.models.workspace import Workspace  # 순환 import 방지 (모듈 끝)
    ws = await db.scalar(
        select(Workspace).where(Workspace.id == workspace_id)
    )
    if ws is None:
        log.warning("email_service: workspace not found id=%s", workspace_id)
        return None

    owner_id = ws.owner_id

    # 2) profile lookup (preferred_language + display_name).
    profile = await db.scalar(
        select(Profile).where(Profile.id == owner_id)
    )
    if profile is None:
        log.warning(
            "email_service: profile missing for owner=%s ws=%s",
            owner_id, workspace_id,
        )
        return None

    # 3) auth.users.email — schema=auth 라 raw SQL.
    sql = text("SELECT email FROM auth.users WHERE id = :id")
    result = await db.execute(sql, {"id": owner_id})
    row = result.first()
    email = row[0] if row else None
    if not email:
        log.warning(
            "email_service: auth.users.email missing for owner=%s ws=%s",
            owner_id, workspace_id,
        )
        return None

    return {
        "user_id": owner_id,
        "email": email,
        "lang": _normalize_lang(profile.preferred_language),
        "display_name": profile.display_name or "",
        "workspace_name": ws.name,
    }


def build_trial_expiry_context(
    *,
    day: int,
    workspace_name: str,
    display_name: str,
    lang: str,
    frontend_url: str,
) -> dict[str, Any]:
    """트라이얼 만료 메일 템플릿 컨텍스트 빌더.

    discount_percent / cta_label / pricing_url / display_name 등 메타.
    Day 별 할인 정책 (SPEC §4-3) 매핑.
    """
    if day not in TRIAL_EXPIRY_DAY_SET:
        raise ValueError(
            f"day must be one of {sorted(TRIAL_EXPIRY_DAYS)}, got {day}"
        )

    # SPEC §4-3 표 정합. duration_label 은 lang 별로 다름 → 템플릿이 표시.
    if day == 7:
        discount_percent, duration_months = 30, 1
        urgency = "limited"  # "3일 한정"
    elif day == 30:
        discount_percent, duration_months = 50, 1
        urgency = "standard"
    else:  # 90
        discount_percent, duration_months = 50, 3
        urgency = "final"  # 최종 제안 + 데모 옵션

    return {
        "day": day,
        "workspace_name": workspace_name,
        "display_name": display_name,
        "discount_percent": discount_percent,
        "duration_months": duration_months,
        "urgency": urgency,
        "include_demo_cta": (day == 90),  # Day 90 만 1:1 데모 CTA
        "pricing_url": f"{frontend_url.rstrip('/')}/{lang}/pricing",
        "demo_url": f"{frontend_url.rstrip('/')}/{lang}/contact?topic=demo",
        "lang": lang,
    }


async def send_trial_expiry_email(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    day: int,
) -> dict[str, Any]:
    """트라이얼 만료 시퀀스 메일 1통 — 단일 워크스페이스 owner 대상.

    반환: ``{sent, skipped, total, recipient}`` (단일 owner 라 list 아닌 단건).
    cron 호출자는 trial_ends_at 기준 day 일치 워크스페이스를 batch 로 처리하지만,
    본 helper 는 워크스페이스 1개 단위로만 발송.

    Phase 2 쿠폰 청크에서 본 함수 호출 직전에 ``_inject_coupon_token(...)`` 같은
    helper 로 컨텍스트에 코드 주입 가능 (현재는 할인 % + URL 만).
    """
    if day not in TRIAL_EXPIRY_DAY_SET:
        raise ValueError(
            f"day must be one of {sorted(TRIAL_EXPIRY_DAYS)}, got {day}"
        )

    settings = get_settings()
    summary: dict[str, Any] = {
        "sent": 0, "skipped": 0, "total": 0, "recipient": None,
    }

    owner = await _resolve_workspace_owner(db, workspace_id=workspace_id)
    if owner is None:
        log.info(
            "email_service: trial_expiry skip — owner unresolved ws=%s day=%s",
            workspace_id, day,
        )
        return summary

    summary["total"] = 1
    lang = owner["lang"]

    try:
        ctx = build_trial_expiry_context(
            day=day,
            workspace_name=owner["workspace_name"],
            display_name=owner["display_name"],
            lang=lang,
            frontend_url=settings.frontend_url,
        )
        html = render_template(_trial_expiry_trigger(day), lang, ctx)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "email_service: trial_expiry render failed ws=%s day=%s lang=%s err=%s",
            workspace_id, day, lang, exc,
        )
        summary["skipped"] = 1
        summary["recipient"] = {**owner, "ok": False, "reason": "render_error"}
        return summary

    subject = _TRIAL_EXPIRY_SUBJECT[day][lang]
    ok = await _send_one(to=owner["email"], subject=subject, html=html)
    if ok:
        summary["sent"] = 1
    else:
        summary["skipped"] = 1
    summary["recipient"] = {
        **owner, "ok": ok, "reason": "sent" if ok else "send_failed",
    }
    return summary


# ─── v1 deprecated stub (leads.py 호출자 보존) ───────────────────────

async def send_report_email(*args: Any, **kwargs: Any) -> None:
    """DEPRECATED — v1 leads/marketing 흐름.

    routers/leads.py 가 이 함수를 호출하지만 leads.py 자체가 v1 dead path
    (002 마이그레이션으로 backing 테이블 DROP). 본 함수는 silent no-op 으로
    보존하고, v1 청소 청크에서 leads.py + tables.py + 본 함수 일괄 제거 예정.
    """
    log.debug("send_report_email (v1 deprecated) called — silent no-op")
    return None
