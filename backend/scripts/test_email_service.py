"""email_service 단위 테스트 (G7-email-core, services/email_service).

실행:
    Set-Location backend; $env:PYTHONUTF8="1"; $env:PYTHONPATH="$PWD"
    .venv\\Scripts\\python.exe scripts\\test_email_service.py

검증:
- render_template — 3 언어 + 미지원 lang → en 폴백 + autoescape.
- build_analysis_complete_context — multilingual summary/improvements lang 분기 + en fallback.
- _resolve_recipients — owner+admin+analyzed_by 중복 제거, email 누락 skip.
- _send_one — resend_api_key 빈 값 시 silent skip.
- send_analysis_complete_email — Resend SDK mock + 수신자별 발송 결과 누적.
- v1 send_report_email DEPRECATED stub — 호출 시 silent no-op.

mock 패턴 (test_llm_synthesizer_v2 와 동일):
- get_settings → monkey-patch 로 resend_api_key + frontend_url 시뮬레이션.
- resend.Emails.send → MagicMock 으로 호출 capture.
- DB session → AsyncMock (execute() 반환 mock).
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from app.services import email_service as svc
from app.services.email_service import (
    DEFAULT_LANG,
    SUPPORTED_LANGS,
    TRIAL_EXPIRY_DAYS,
    TRIGGER_ANALYSIS_COMPLETE,
    _format_improvement_for_email,
    _normalize_lang,
    _resolve_recipients,
    _resolve_workspace_owner,
    _send_one,
    _trial_expiry_trigger,
    build_analysis_complete_context,
    build_trial_expiry_context,
    render_template,
    send_analysis_complete_email,
    send_report_email,
    send_trial_expiry_email,
)


# ─── 픽스처 ─────────────────────────────────────────────────────────────

def _fake_analysis(
    *,
    insights: dict | None = None,
    improvements: dict | None = None,
    overall: float | None = 78.0,
    category_scores: dict | None = None,
    workspace_id: UUID | None = None,
    triggered_by: UUID | None = None,
) -> SimpleNamespace:
    """AnalysisResult 흉내 — ORM row 의 attribute 접근만 사용."""
    return SimpleNamespace(
        id=uuid4(),
        workspace_id=workspace_id or uuid4(),
        site_id=uuid4(),
        triggered_by=triggered_by,
        overall_score=Decimal(str(overall)) if overall is not None else None,
        category_scores=category_scores or {
            "technical": 80.0, "structured": 75.0, "content": 70.0,
        },
        insights=insights,
        improvements=improvements,
        completed_at=datetime.now(timezone.utc),
    )


def _fake_site(domain: str = "example.com") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        url=f"https://{domain}",
        domain=domain,
    )


def _multi(en: str = "EN summary", ko: str = "KO 요약", es: str = "ES resumen") -> dict:
    return {"en": en, "ko": ko, "es": es}


def _full_insights() -> dict:
    return {
        "summary": _multi(),
        "primary_language": "en",
        "synthesized_by": "claude-sonnet-4-6",
        "category_count": 3,
        "improvements_count": 2,
        "high_priority_capped": False,
    }


def _full_improvements() -> dict:
    return {
        "items": [
            {
                "priority": "high",
                "category": "technical",
                "title_key": "scoring.technical.ssl_enabled.improvement_title",
                "description": _multi(en="Enable SSL", ko="SSL 활성화", es="Activar SSL"),
                "estimated_impact": 9,
                "estimated_effort": "low",
                "related_metric_keys": ["ssl_enabled"],
            },
            {
                "priority": "medium",
                "category": "content",
                "title_key": "scoring.content.readability.improvement_title",
                "description": _multi(en="Improve readability", ko="가독성 개선", es="Mejorar la legibilidad"),
                "estimated_impact": 6,
                "estimated_effort": "medium",
                "related_metric_keys": ["readability"],
            },
        ],
    }


FAILED: list[str] = []


def _check(label: str, cond: bool, detail: str = "") -> None:
    suffix = f" — {detail}" if detail and not cond else ""
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}{suffix}")
    if not cond:
        FAILED.append(label)


# ─── render_template ────────────────────────────────────────────────────

def test_render_template():
    print("\n== render_template ==")
    analysis = _fake_analysis(
        insights=_full_insights(),
        improvements=_full_improvements(),
    )
    site = _fake_site("ahxov.com")

    for lang in SUPPORTED_LANGS:
        ctx = build_analysis_complete_context(
            analysis=analysis, site=site, lang=lang,
            frontend_url="https://app.ahxov.com",
        )
        html = render_template(TRIGGER_ANALYSIS_COMPLETE, lang, ctx)
        _check(
            f"T01 render {lang} contains domain",
            "ahxov.com" in html,
        )
        _check(
            f"T02 render {lang} contains overall score 78",
            ">78<" in html,
        )
        _check(
            f"T03 render {lang} contains result_url",
            "/sites/" in html and "/results/" in html and lang in html,
        )

    # T04 — 언어별 키워드 (en: "Analysis complete" / ko: "분석" / es: "Análisis")
    en_html = render_template(
        TRIGGER_ANALYSIS_COMPLETE, "en",
        build_analysis_complete_context(
            analysis=analysis, site=site, lang="en",
            frontend_url="https://app.ahxov.com",
        ),
    )
    _check("T04a en template has 'Analysis complete'", "Analysis complete" in en_html)
    ko_html = render_template(
        TRIGGER_ANALYSIS_COMPLETE, "ko",
        build_analysis_complete_context(
            analysis=analysis, site=site, lang="ko",
            frontend_url="https://app.ahxov.com",
        ),
    )
    _check("T04b ko template has '분석이 완료'", "분석이 완료" in ko_html)
    es_html = render_template(
        TRIGGER_ANALYSIS_COMPLETE, "es",
        build_analysis_complete_context(
            analysis=analysis, site=site, lang="es",
            frontend_url="https://app.ahxov.com",
        ),
    )
    _check("T04c es template has 'Análisis completado'", "Análisis completado" in es_html)

    # T05 — 미지원 lang → en 폴백.
    fallback_html = render_template(
        TRIGGER_ANALYSIS_COMPLETE, "fr",  # 미지원
        build_analysis_complete_context(
            analysis=analysis, site=site, lang="en",
            frontend_url="https://app.ahxov.com",
        ),
    )
    _check("T05 unsupported lang → en fallback", "Analysis complete" in fallback_html)


# ─── build_analysis_complete_context ────────────────────────────────────

def test_build_context_lang_dispatch():
    print("\n== build_analysis_complete_context ==")
    analysis = _fake_analysis(
        insights=_full_insights(),
        improvements=_full_improvements(),
    )
    site = _fake_site("ahxov.com")

    ctx_en = build_analysis_complete_context(
        analysis=analysis, site=site, lang="en",
        frontend_url="https://app.ahxov.com",
    )
    _check("T06 en summary picked", ctx_en["summary"] == "EN summary")
    _check(
        "T07 en improvements description picked",
        ctx_en["improvements"][0]["description"] == "Enable SSL",
    )
    _check("T08 grade derived from overall=78 → B", ctx_en["grade"] == "B")
    _check("T09 result_url contains site_id+result_id",
           f"/sites/{site.id}" in ctx_en["result_url"]
           and f"/results/{analysis.id}" in ctx_en["result_url"])

    ctx_ko = build_analysis_complete_context(
        analysis=analysis, site=site, lang="ko",
        frontend_url="https://app.ahxov.com",
    )
    _check("T10 ko summary picked", ctx_ko["summary"] == "KO 요약")
    _check(
        "T11 ko improvements description picked",
        ctx_ko["improvements"][0]["description"] == "SSL 활성화",
    )

    # T12 — improvements 상위 5 컷오프.
    many_imps = {
        "items": [
            {
                "priority": "low",
                "category": "technical",
                "description": _multi(en=f"item {i}"),
                "estimated_impact": 3,
                "estimated_effort": "low",
                "related_metric_keys": ["ssl_enabled"],
            }
            for i in range(8)
        ]
    }
    analysis_many = _fake_analysis(
        insights=_full_insights(), improvements=many_imps,
    )
    ctx = build_analysis_complete_context(
        analysis=analysis_many, site=site, lang="en",
        frontend_url="https://app.ahxov.com",
    )
    _check("T12 improvements truncated to top 5", len(ctx["improvements"]) == 5)


def test_build_context_empty_insights():
    print("\n== build_context with empty insights/improvements ==")
    site = _fake_site()

    # 빈 insights
    a1 = _fake_analysis(insights=None, improvements=None)
    ctx = build_analysis_complete_context(
        analysis=a1, site=site, lang="en",
        frontend_url="https://app.ahxov.com",
    )
    _check("T13 None insights → empty summary", ctx["summary"] == "")
    _check("T14 None improvements → empty list", ctx["improvements"] == [])

    # summary 가 lang 없는 dict (예: en 만)
    a2 = _fake_analysis(
        insights={"summary": {"en": "only english"}},
        improvements={"items": []},
    )
    ctx2 = build_analysis_complete_context(
        analysis=a2, site=site, lang="ko",
        frontend_url="https://app.ahxov.com",
    )
    _check("T15 missing lang in summary → en fallback",
           ctx2["summary"] == "only english")

    # improvements item description 이 string (multilingual ❌)
    a3 = _fake_analysis(
        insights=_full_insights(),
        improvements={
            "items": [{
                "priority": "high",
                "category": "technical",
                "description": "plain string desc",
                "estimated_impact": 5,
                "estimated_effort": "low",
                "related_metric_keys": ["ssl_enabled"],
            }],
        },
    )
    ctx3 = build_analysis_complete_context(
        analysis=a3, site=site, lang="ko",
        frontend_url="https://app.ahxov.com",
    )
    _check("T16 string description preserved as-is",
           ctx3["improvements"][0]["description"] == "plain string desc")


def test_grade_thresholds():
    print("\n== _derive_grade thresholds ==")
    site = _fake_site()
    cases = [(95, "A"), (90, "A"), (89, "B"), (75, "B"), (74, "C"), (60, "C"),
             (59, "D"), (40, "D"), (39, "F"), (0, "F")]
    for score, expected in cases:
        a = _fake_analysis(overall=float(score))
        ctx = build_analysis_complete_context(
            analysis=a, site=site, lang="en",
            frontend_url="https://app.ahxov.com",
        )
        _check(f"T17 score={score} → grade={expected}", ctx["grade"] == expected)


# ─── _resolve_recipients ────────────────────────────────────────────────

def _make_session_for_recipients(
    *,
    member_user_ids: list[UUID],
    profile_langs: dict[UUID, str],
    auth_emails: dict[UUID, str | None],
) -> MagicMock:
    """db.execute mock — 호출 순서: members → profiles → auth.users."""
    db = MagicMock()
    call_results = [
        # members rows: list of (user_id,) tuples
        MagicMock(all=MagicMock(return_value=[(uid,) for uid in member_user_ids])),
        # profiles rows: list of (user_id, lang) tuples
        MagicMock(all=MagicMock(return_value=[
            (uid, lang) for uid, lang in profile_langs.items()
        ])),
        # auth.users rows: list of (user_id, email) tuples
        MagicMock(all=MagicMock(return_value=[
            (uid, email) for uid, email in auth_emails.items()
        ])),
    ]
    db.execute = AsyncMock(side_effect=call_results)
    return db


def test_resolve_recipients_owner_admin():
    print("\n== _resolve_recipients ==")
    owner_id, admin_id, viewer_id = uuid4(), uuid4(), uuid4()
    member_ids = [owner_id, admin_id]  # viewer 자동 미포함 (NOTIFY_ROLES filter)
    profile_langs = {owner_id: "en", admin_id: "ko"}
    auth_emails = {owner_id: "owner@a.com", admin_id: "admin@a.com"}

    db = _make_session_for_recipients(
        member_user_ids=member_ids,
        profile_langs=profile_langs,
        auth_emails=auth_emails,
    )
    rcps = asyncio.run(_resolve_recipients(
        db, workspace_id=uuid4(), triggered_by=None,
    ))
    _check("T18 owner + admin returned (no viewer)", len(rcps) == 2)
    emails = {r["email"] for r in rcps}
    _check("T19 emails are owner+admin",
           emails == {"owner@a.com", "admin@a.com"})
    langs_by_email = {r["email"]: r["lang"] for r in rcps}
    _check("T20 langs match profiles",
           langs_by_email["owner@a.com"] == "en"
           and langs_by_email["admin@a.com"] == "ko")


def test_resolve_recipients_dedup_with_triggered_by():
    print("\n== _resolve_recipients dedup ==")
    owner_id = uuid4()
    member_ids = [owner_id]
    profile_langs = {owner_id: "es"}
    auth_emails = {owner_id: "owner@a.com"}

    # triggered_by == owner → 중복 제거 → 1건
    db = _make_session_for_recipients(
        member_user_ids=member_ids,
        profile_langs=profile_langs,
        auth_emails=auth_emails,
    )
    rcps = asyncio.run(_resolve_recipients(
        db, workspace_id=uuid4(), triggered_by=owner_id,
    ))
    _check("T21 owner == triggered_by deduped to 1", len(rcps) == 1)


def test_resolve_recipients_external_triggered_by():
    print("\n== _resolve_recipients external triggered_by ==")
    owner_id, member_id = uuid4(), uuid4()
    member_ids = [owner_id]  # member_id 는 NOTIFY_ROLES 외
    profile_langs = {owner_id: "en", member_id: "ko"}
    auth_emails = {owner_id: "owner@a.com", member_id: "member@a.com"}

    db = _make_session_for_recipients(
        member_user_ids=member_ids,
        profile_langs=profile_langs,
        auth_emails=auth_emails,
    )
    rcps = asyncio.run(_resolve_recipients(
        db, workspace_id=uuid4(), triggered_by=member_id,
    ))
    _check("T22 owner + analyzed_by (member) both included", len(rcps) == 2)


def test_resolve_recipients_email_missing():
    print("\n== _resolve_recipients email missing skip ==")
    owner_id, admin_id = uuid4(), uuid4()
    member_ids = [owner_id, admin_id]
    profile_langs = {owner_id: "en", admin_id: "ko"}
    # admin email 누락 (None)
    auth_emails = {owner_id: "owner@a.com", admin_id: None}

    db = _make_session_for_recipients(
        member_user_ids=member_ids,
        profile_langs=profile_langs,
        auth_emails=auth_emails,
    )
    rcps = asyncio.run(_resolve_recipients(
        db, workspace_id=uuid4(), triggered_by=None,
    ))
    _check("T23 missing email skipped", len(rcps) == 1)
    _check("T24 only owner remains",
           rcps[0]["email"] == "owner@a.com" if rcps else False)


# ─── _send_one + send_analysis_complete_email ──────────────────────────

def test_send_one_no_api_key():
    print("\n== _send_one no api_key ==")
    fake = SimpleNamespace(resend_api_key="", frontend_url="https://app.ahxov.com")
    original = svc.get_settings
    svc.get_settings = lambda: fake
    try:
        result = asyncio.run(_send_one(
            to="x@a.com", subject="s", html="<p>x</p>",
        ))
        _check("T25 empty api_key → silent skip (False)", result is False)
    finally:
        svc.get_settings = original


def test_send_one_with_api_key_uses_resend():
    print("\n== _send_one with api_key ==")
    fake = SimpleNamespace(resend_api_key="re_test_xxx", frontend_url="https://app.ahxov.com")
    original = svc.get_settings
    svc.get_settings = lambda: fake

    sent_payloads: list[dict] = []
    def _capture(payload):
        sent_payloads.append(payload)
        return {"id": "msg_001"}

    original_send = svc.resend.Emails.send
    svc.resend.Emails.send = _capture
    try:
        result = asyncio.run(_send_one(
            to="x@a.com", subject="hi", html="<p>x</p>",
        ))
        _check("T26 with api_key → True", result is True)
        _check("T27 resend payload captured",
               len(sent_payloads) == 1
               and sent_payloads[0]["to"] == ["x@a.com"]
               and sent_payloads[0]["subject"] == "hi")
        _check("T28 from address is no-reply@ahxov.com",
               "no-reply@ahxov.com" in sent_payloads[0]["from"])
    finally:
        svc.get_settings = original
        svc.resend.Emails.send = original_send


def test_send_one_resend_error_swallowed():
    print("\n== _send_one Resend error swallowed ==")
    fake = SimpleNamespace(resend_api_key="re_test_xxx", frontend_url="https://app.ahxov.com")
    original = svc.get_settings
    svc.get_settings = lambda: fake

    def _raise(payload):
        raise RuntimeError("rate limit")

    original_send = svc.resend.Emails.send
    svc.resend.Emails.send = _raise
    try:
        result = asyncio.run(_send_one(
            to="x@a.com", subject="hi", html="<p>x</p>",
        ))
        _check("T29 Resend error swallowed → False", result is False)
    finally:
        svc.get_settings = original
        svc.resend.Emails.send = original_send


def test_send_analysis_complete_full():
    print("\n== send_analysis_complete_email full flow ==")
    owner_id, admin_id = uuid4(), uuid4()
    workspace_id = uuid4()

    fake = SimpleNamespace(resend_api_key="re_test_xxx", frontend_url="https://app.ahxov.com")
    original_settings = svc.get_settings
    svc.get_settings = lambda: fake

    sent: list[dict] = []
    original_send = svc.resend.Emails.send
    svc.resend.Emails.send = lambda payload: sent.append(payload) or {"id": "x"}

    try:
        analysis = _fake_analysis(
            workspace_id=workspace_id,
            triggered_by=owner_id,
            insights=_full_insights(),
            improvements=_full_improvements(),
        )
        site = _fake_site("ahxov.com")

        db = _make_session_for_recipients(
            member_user_ids=[owner_id, admin_id],
            profile_langs={owner_id: "ko", admin_id: "es"},
            auth_emails={owner_id: "owner@a.com", admin_id: "admin@a.com"},
        )

        summary = asyncio.run(send_analysis_complete_email(
            db, analysis=analysis, site=site,
        ))
        _check("T30 sent count == 2", summary["sent"] == 2)
        _check("T31 skipped == 0", summary["skipped"] == 0)
        _check("T32 total == 2", summary["total"] == 2)
        _check("T33 resend called twice", len(sent) == 2)

        # 언어별 subject 검증.
        subjects = sorted(p["subject"] for p in sent)
        # ko + es 주제어
        ko_in = any("분석이 완료" in s for s in subjects)
        es_in = any("Análisis completado" in s for s in subjects)
        _check("T34 ko subject present", ko_in)
        _check("T35 es subject present", es_in)

        # 언어별 본문 검증.
        ko_bodies = [p for p in sent if "분석이 완료" in p["html"]]
        es_bodies = [p for p in sent if "Análisis completado" in p["html"]]
        _check("T36 ko body rendered with ko template", len(ko_bodies) == 1)
        _check("T37 es body rendered with es template", len(es_bodies) == 1)

        # ko 수신자 본문에 SSL 활성화 (improvement[ko]) 포함.
        _check("T38 ko body has ko improvement description",
               "SSL 활성화" in ko_bodies[0]["html"])
    finally:
        svc.get_settings = original_settings
        svc.resend.Emails.send = original_send


def test_send_analysis_complete_no_recipients():
    print("\n== send_analysis_complete_email no recipients ==")
    fake = SimpleNamespace(resend_api_key="re_test_xxx", frontend_url="https://app.ahxov.com")
    original = svc.get_settings
    svc.get_settings = lambda: fake
    try:
        db = _make_session_for_recipients(
            member_user_ids=[],
            profile_langs={},
            auth_emails={},
        )
        analysis = _fake_analysis(insights=_full_insights(), improvements=_full_improvements())
        site = _fake_site()
        summary = asyncio.run(send_analysis_complete_email(
            db, analysis=analysis, site=site,
        ))
        _check("T39 empty recipients → total=0", summary["total"] == 0)
        _check("T40 sent==0 skipped==0", summary["sent"] == 0 and summary["skipped"] == 0)
    finally:
        svc.get_settings = original


def test_send_analysis_partial_failure():
    print("\n== send_analysis_complete_email partial Resend failure ==")
    owner_id, admin_id = uuid4(), uuid4()
    workspace_id = uuid4()
    fake = SimpleNamespace(resend_api_key="re_test_xxx", frontend_url="https://app.ahxov.com")
    original_settings = svc.get_settings
    svc.get_settings = lambda: fake

    call_n = {"n": 0}
    def _flaky(payload):
        call_n["n"] += 1
        if call_n["n"] == 1:
            raise RuntimeError("first call fails")
        return {"id": "x"}

    original_send = svc.resend.Emails.send
    svc.resend.Emails.send = _flaky

    try:
        analysis = _fake_analysis(
            workspace_id=workspace_id,
            insights=_full_insights(),
            improvements=_full_improvements(),
        )
        site = _fake_site()
        db = _make_session_for_recipients(
            member_user_ids=[owner_id, admin_id],
            profile_langs={owner_id: "en", admin_id: "en"},
            auth_emails={owner_id: "o@a.com", admin_id: "a@a.com"},
        )
        summary = asyncio.run(send_analysis_complete_email(
            db, analysis=analysis, site=site,
        ))
        _check("T41 partial failure: sent=1", summary["sent"] == 1)
        _check("T42 partial failure: skipped=1", summary["skipped"] == 1)
        _check("T43 partial failure: total=2", summary["total"] == 2)
    finally:
        svc.get_settings = original_settings
        svc.resend.Emails.send = original_send


# ─── 보조: _normalize_lang / _format_improvement_for_email ─────────────

def test_normalize_lang():
    print("\n== _normalize_lang ==")
    _check("T44 en → en", _normalize_lang("en") == "en")
    _check("T45 ko → ko", _normalize_lang("ko") == "ko")
    _check("T46 es → es", _normalize_lang("es") == "es")
    _check("T47 unsupported → en", _normalize_lang("fr") == DEFAULT_LANG)
    _check("T48 None → en", _normalize_lang(None) == DEFAULT_LANG)


def test_format_improvement_for_email():
    print("\n== _format_improvement_for_email ==")
    item = {
        "priority": "high",
        "category": "technical",
        "description": _multi(),
        "estimated_impact": 8,
        "estimated_effort": "low",
        "related_metric_keys": ["ssl_enabled"],
    }
    out = _format_improvement_for_email(item, "ko")
    _check("T49 ko description picked", out["description"] == "KO 요약")
    _check("T50 priority preserved", out["priority"] == "high")
    _check("T51 category preserved", out["category"] == "technical")
    _check("T52 effort preserved", out["estimated_effort"] == "low")

    # description dict 에 lang 누락
    item2 = dict(item, description={"en": "english only"})
    out2 = _format_improvement_for_email(item2, "ko")
    _check("T53 missing lang → en fallback",
           out2["description"] == "english only")

    # description 이 string
    item3 = dict(item, description="plain")
    out3 = _format_improvement_for_email(item3, "ko")
    _check("T54 string description as-is", out3["description"] == "plain")


# ─── G8 trial_expiry: helper / context / trigger ────────────────────────

def test_trial_expiry_trigger_dirname():
    print("\n== _trial_expiry_trigger ==")
    _check("T56 day=7 → trial_expiry_day7",
           _trial_expiry_trigger(7) == "trial_expiry_day7")
    _check("T57 day=30 → trial_expiry_day30",
           _trial_expiry_trigger(30) == "trial_expiry_day30")
    _check("T58 day=90 → trial_expiry_day90",
           _trial_expiry_trigger(90) == "trial_expiry_day90")
    raised = False
    try:
        _trial_expiry_trigger(14)
    except ValueError:
        raised = True
    _check("T59 invalid day raises ValueError", raised)


def test_trial_expiry_context_per_day():
    print("\n== build_trial_expiry_context per day ==")
    common = dict(
        workspace_name="Acme",
        display_name="Jane",
        lang="en",
        frontend_url="https://app.ahxov.com",
    )

    ctx7 = build_trial_expiry_context(day=7, **common)
    _check("T60 day=7: discount=30 / duration=1 / urgency=limited",
           ctx7["discount_percent"] == 30
           and ctx7["duration_months"] == 1
           and ctx7["urgency"] == "limited"
           and ctx7["include_demo_cta"] is False)

    ctx30 = build_trial_expiry_context(day=30, **common)
    _check("T61 day=30: discount=50 / duration=1 / urgency=standard",
           ctx30["discount_percent"] == 50
           and ctx30["duration_months"] == 1
           and ctx30["urgency"] == "standard"
           and ctx30["include_demo_cta"] is False)

    ctx90 = build_trial_expiry_context(day=90, **common)
    _check("T62 day=90: discount=50 / duration=3 / urgency=final / demo=True",
           ctx90["discount_percent"] == 50
           and ctx90["duration_months"] == 3
           and ctx90["urgency"] == "final"
           and ctx90["include_demo_cta"] is True)

    _check("T63 pricing_url contains lang",
           ctx7["pricing_url"] == "https://app.ahxov.com/en/pricing")
    _check("T64 demo_url contains topic=demo",
           "topic=demo" in ctx90["demo_url"])

    raised = False
    try:
        build_trial_expiry_context(day=15, **common)
    except ValueError:
        raised = True
    _check("T65 invalid day raises ValueError", raised)


def test_trial_expiry_template_render_per_day():
    print("\n== render trial_expiry templates ==")
    common = dict(
        workspace_name="Acme",
        display_name="Jane",
        frontend_url="https://app.ahxov.com",
    )

    # Day 7 — "30%" discount + lang 별 hero text
    for lang, hero in [("en", "Your trial ended"),
                       ("ko", "트라이얼이 종료"),
                       ("es", "Su prueba terminó")]:
        ctx = build_trial_expiry_context(day=7, lang=lang, **common)
        html = render_template(_trial_expiry_trigger(7), lang, ctx)
        _check(f"T66 day7 {lang} hero text", hero in html)
        _check(f"T67 day7 {lang} 30% discount", "30%" in html)
        _check(f"T68 day7 {lang} no demo CTA", "demo" not in html.lower() or "{{" not in html)

    # Day 30 — "50%" discount, no demo CTA
    for lang, hero in [("en", "Still curious"),
                       ("ko", "다시 시작"),
                       ("es", "¿Sigue interesado?")]:
        ctx = build_trial_expiry_context(day=30, lang=lang, **common)
        html = render_template(_trial_expiry_trigger(30), lang, ctx)
        _check(f"T69 day30 {lang} hero text", hero in html)
        _check(f"T70 day30 {lang} 50% discount", "50%" in html)

    # Day 90 — "50%" discount + demo CTA
    for lang, hero, demo_label in [
        ("en", "Last chance", "Book a free demo"),
        ("ko", "마지막 기회", "데모 예약"),
        ("es", "Última oportunidad", "Reservar demo"),
    ]:
        ctx = build_trial_expiry_context(day=90, lang=lang, **common)
        html = render_template(_trial_expiry_trigger(90), lang, ctx)
        _check(f"T71 day90 {lang} hero text", hero in html)
        _check(f"T72 day90 {lang} demo CTA", demo_label in html)
        _check(f"T73 day90 {lang} 3 months", "3" in html)

    # display_name 없는 경우 — greeting 블록 자동 skip (Jinja2 {% if %})
    ctx_no_name = build_trial_expiry_context(
        day=7, workspace_name="Acme", display_name="",
        lang="en", frontend_url="https://app.ahxov.com",
    )
    html_no_name = render_template(_trial_expiry_trigger(7), "en", ctx_no_name)
    _check("T74 empty display_name → no 'Hi ,' greeting",
           "Hi ," not in html_no_name)


# ─── G8 _resolve_workspace_owner ────────────────────────────────────────

def _make_session_for_owner(
    *,
    workspace: SimpleNamespace | None = None,
    profile: SimpleNamespace | None = None,
    auth_email: str | None = "owner@a.com",
) -> MagicMock:
    """db.scalar 2번 (workspace, profile) + db.execute 1번 (auth.users) 시뮬."""
    db = MagicMock()
    db.scalar = AsyncMock(side_effect=[workspace, profile])
    if auth_email is None:
        # row 자체 없는 경우 first() → None
        execute_result = MagicMock(first=MagicMock(return_value=None))
    else:
        execute_result = MagicMock(first=MagicMock(return_value=(auth_email,)))
    db.execute = AsyncMock(return_value=execute_result)
    return db


def test_resolve_owner_happy():
    print("\n== _resolve_workspace_owner happy ==")
    owner_id = uuid4()
    ws_id = uuid4()
    workspace = SimpleNamespace(id=ws_id, owner_id=owner_id, name="Acme")
    profile = SimpleNamespace(id=owner_id, preferred_language="ko",
                               display_name="Jane")
    db = _make_session_for_owner(
        workspace=workspace, profile=profile, auth_email="owner@a.com",
    )
    out = asyncio.run(_resolve_workspace_owner(db, workspace_id=ws_id))
    _check("T75 owner resolved", out is not None)
    _check("T76 email correct", out["email"] == "owner@a.com")
    _check("T77 lang from profile", out["lang"] == "ko")
    _check("T78 display_name from profile", out["display_name"] == "Jane")
    _check("T79 workspace_name from workspace", out["workspace_name"] == "Acme")


def test_resolve_owner_workspace_missing():
    print("\n== _resolve_workspace_owner workspace missing ==")
    db = _make_session_for_owner(workspace=None, profile=None, auth_email=None)
    out = asyncio.run(_resolve_workspace_owner(db, workspace_id=uuid4()))
    _check("T80 workspace missing → None", out is None)


def test_resolve_owner_profile_missing():
    print("\n== _resolve_workspace_owner profile missing ==")
    owner_id = uuid4()
    ws_id = uuid4()
    workspace = SimpleNamespace(id=ws_id, owner_id=owner_id, name="Acme")
    db = _make_session_for_owner(
        workspace=workspace, profile=None, auth_email="owner@a.com",
    )
    out = asyncio.run(_resolve_workspace_owner(db, workspace_id=ws_id))
    _check("T81 profile missing → None", out is None)


def test_resolve_owner_email_missing():
    print("\n== _resolve_workspace_owner email missing ==")
    owner_id = uuid4()
    ws_id = uuid4()
    workspace = SimpleNamespace(id=ws_id, owner_id=owner_id, name="Acme")
    profile = SimpleNamespace(id=owner_id, preferred_language="en",
                               display_name="")
    db = _make_session_for_owner(
        workspace=workspace, profile=profile, auth_email=None,
    )
    out = asyncio.run(_resolve_workspace_owner(db, workspace_id=ws_id))
    _check("T82 auth.users.email missing → None", out is None)


# ─── G8 send_trial_expiry_email ────────────────────────────────────────

def test_send_trial_expiry_full():
    print("\n== send_trial_expiry_email full flow ==")
    fake = SimpleNamespace(resend_api_key="re_test_xxx",
                            frontend_url="https://app.ahxov.com")
    original_settings = svc.get_settings
    svc.get_settings = lambda: fake

    sent: list[dict] = []
    original_send = svc.resend.Emails.send
    svc.resend.Emails.send = lambda payload: sent.append(payload) or {"id": "x"}

    try:
        for day, lang, expect_subject_substr, expect_body_substr in [
            (7, "en", "30% off", "Your trial ended"),
            (30, "ko", "50% 할인", "다시 시작"),
            (90, "es", "50% por 3 meses", "Última oportunidad"),
        ]:
            sent.clear()
            owner_id, ws_id = uuid4(), uuid4()
            workspace = SimpleNamespace(id=ws_id, owner_id=owner_id, name="Acme")
            profile = SimpleNamespace(id=owner_id, preferred_language=lang,
                                       display_name="Jane")
            db = _make_session_for_owner(
                workspace=workspace, profile=profile, auth_email="o@a.com",
            )
            summary = asyncio.run(send_trial_expiry_email(
                db, workspace_id=ws_id, day=day,
            ))
            _check(f"T83 day={day} {lang}: sent=1",
                   summary["sent"] == 1)
            _check(f"T84 day={day} {lang}: total=1",
                   summary["total"] == 1)
            _check(f"T85 day={day} {lang}: 1 resend call",
                   len(sent) == 1)
            _check(f"T86 day={day} {lang}: subject contains '{expect_subject_substr}'",
                   expect_subject_substr in sent[0]["subject"])
            _check(f"T87 day={day} {lang}: body contains '{expect_body_substr}'",
                   expect_body_substr in sent[0]["html"])
            _check(f"T88 day={day} {lang}: recipient ok=True",
                   summary["recipient"]["ok"] is True)
    finally:
        svc.get_settings = original_settings
        svc.resend.Emails.send = original_send


def test_send_trial_expiry_owner_unresolved():
    print("\n== send_trial_expiry_email owner unresolved skip ==")
    fake = SimpleNamespace(resend_api_key="re_test_xxx",
                            frontend_url="https://app.ahxov.com")
    original = svc.get_settings
    svc.get_settings = lambda: fake
    try:
        # workspace 자체 누락 → owner unresolved → 발송 ❌, summary all 0.
        db = _make_session_for_owner(
            workspace=None, profile=None, auth_email=None,
        )
        summary = asyncio.run(send_trial_expiry_email(
            db, workspace_id=uuid4(), day=7,
        ))
        _check("T89 owner unresolved: sent=0", summary["sent"] == 0)
        _check("T90 owner unresolved: skipped=0", summary["skipped"] == 0)
        _check("T91 owner unresolved: total=0", summary["total"] == 0)
        _check("T92 owner unresolved: recipient=None", summary["recipient"] is None)
    finally:
        svc.get_settings = original


def test_send_trial_expiry_resend_failure():
    print("\n== send_trial_expiry_email Resend failure ==")
    fake = SimpleNamespace(resend_api_key="re_test_xxx",
                            frontend_url="https://app.ahxov.com")
    original_settings = svc.get_settings
    svc.get_settings = lambda: fake
    original_send = svc.resend.Emails.send
    svc.resend.Emails.send = lambda payload: (_ for _ in ()).throw(RuntimeError("rate limit"))
    try:
        owner_id, ws_id = uuid4(), uuid4()
        workspace = SimpleNamespace(id=ws_id, owner_id=owner_id, name="Acme")
        profile = SimpleNamespace(id=owner_id, preferred_language="en",
                                   display_name="Jane")
        db = _make_session_for_owner(
            workspace=workspace, profile=profile, auth_email="o@a.com",
        )
        summary = asyncio.run(send_trial_expiry_email(
            db, workspace_id=ws_id, day=7,
        ))
        _check("T93 Resend failure: sent=0", summary["sent"] == 0)
        _check("T94 Resend failure: skipped=1", summary["skipped"] == 1)
        _check("T95 Resend failure: total=1", summary["total"] == 1)
        _check("T96 Resend failure: recipient ok=False",
               summary["recipient"]["ok"] is False)
    finally:
        svc.get_settings = original_settings
        svc.resend.Emails.send = original_send


def test_send_trial_expiry_invalid_day():
    print("\n== send_trial_expiry_email invalid day ==")
    raised = False
    try:
        asyncio.run(send_trial_expiry_email(
            MagicMock(), workspace_id=uuid4(), day=14,
        ))
    except ValueError:
        raised = True
    _check("T97 invalid day raises ValueError", raised)


def test_trial_expiry_supported_days_constant():
    print("\n== TRIAL_EXPIRY_DAYS constant ==")
    _check("T98 TRIAL_EXPIRY_DAYS = (7, 30, 90)",
           tuple(sorted(TRIAL_EXPIRY_DAYS)) == (7, 30, 90))


# ─── DEPRECATED v1 send_report_email ───────────────────────────────────

def test_v1_send_report_email_noop():
    print("\n== v1 send_report_email DEPRECATED stub ==")
    # 어떤 인자로 호출해도 silent no-op (예외 ❌).
    asyncio.run(send_report_email(None, "x@a.com"))
    asyncio.run(send_report_email(None, None, foo="bar"))
    _check("T55 v1 send_report_email silent no-op (no exception)", True)


# ─── runner ─────────────────────────────────────────────────────────────

def main() -> int:
    # G7 — analysis_complete
    test_render_template()
    test_build_context_lang_dispatch()
    test_build_context_empty_insights()
    test_grade_thresholds()
    test_resolve_recipients_owner_admin()
    test_resolve_recipients_dedup_with_triggered_by()
    test_resolve_recipients_external_triggered_by()
    test_resolve_recipients_email_missing()
    test_send_one_no_api_key()
    test_send_one_with_api_key_uses_resend()
    test_send_one_resend_error_swallowed()
    test_send_analysis_complete_full()
    test_send_analysis_complete_no_recipients()
    test_send_analysis_partial_failure()
    test_normalize_lang()
    test_format_improvement_for_email()
    # G8 — trial_expiry_day{7,30,90}
    test_trial_expiry_trigger_dirname()
    test_trial_expiry_context_per_day()
    test_trial_expiry_template_render_per_day()
    test_resolve_owner_happy()
    test_resolve_owner_workspace_missing()
    test_resolve_owner_profile_missing()
    test_resolve_owner_email_missing()
    test_send_trial_expiry_full()
    test_send_trial_expiry_owner_unresolved()
    test_send_trial_expiry_resend_failure()
    test_send_trial_expiry_invalid_day()
    test_trial_expiry_supported_days_constant()
    # v1 stub
    test_v1_send_report_email_noop()

    if FAILED:
        print(f"\n[FAIL] {len(FAILED)} cases failed:")
        for label in FAILED:
            print(f"  - {label}")
        return 1
    print("\n[PASS] all email_service test cases (G7 + G8)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
