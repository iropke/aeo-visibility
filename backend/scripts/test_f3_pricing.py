"""F3-pricing 단위 테스트 — rate_limit / contact 스키마 / plans 정렬 / contact 알림 메일.

실행:
    Set-Location backend; $env:PYTHONUTF8="1"; $env:PYTHONPATH="$PWD"
    .venv\\Scripts\\python.exe scripts\\test_f3_pricing.py

검증:
    [rate_limit]
    - check_and_record  — 한도 내 통과, 한도 초과 차단, window 후 회복
    - hash_ip           — 동일 IP+salt 결정성, 다른 salt 다른 hash
    - reset_buckets     — 키별/전체 reset

    [schemas/contact]
    - ContactCreate     — 필수 필드, name/email/message 검증, topic 기본값
    - honeypot website  — 임의 string 허용 (라우터에서 분기)

    [routers/plans]
    - _PLAN_DISPLAY_ORDER 키 정렬 (free → enterprise → unknown)

    [email_service.send_contact_notification]
    - api_key 빈 값 → silent skip → False
    - notification_to 빈 값 → False
    - render → Resend send mock 호출 + topic 별 subject + from override
"""
from __future__ import annotations

import asyncio
import sys
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from app.models.contact_submission import ContactStatus, ContactTopic
from app.routers.plans import _PLAN_DISPLAY_ORDER
from app.schemas.contact import ContactCreate
from app.services import email_service as svc
from app.services.email_service import (
    TRIGGER_CONTACT_NOTIFICATION,
    build_contact_notification_context,
    send_contact_notification,
)
from app.services.rate_limit import (
    DEFAULT_MAX_REQUESTS,
    check_and_record,
    hash_ip,
    reset_buckets,
)


FAILED: list[str] = []


def _check(label: str, cond: bool, detail: str = "") -> None:
    suffix = f" — {detail}" if detail and not cond else ""
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}{suffix}")
    if not cond:
        FAILED.append(label)


# ─── rate_limit ─────────────────────────────────────────────────────────

def test_rate_limit_within_quota():
    print("\n== rate_limit within quota ==")
    reset_buckets()
    key = "k1"
    results = [
        asyncio.run(check_and_record(key, max_requests=3, window_s=60))
        for _ in range(3)
    ]
    _check("T01 first 3 requests pass", all(results))


def test_rate_limit_exceeds_quota():
    print("\n== rate_limit exceeds quota ==")
    reset_buckets()
    key = "k2"
    for _ in range(3):
        asyncio.run(check_and_record(key, max_requests=3, window_s=60))
    blocked = asyncio.run(check_and_record(key, max_requests=3, window_s=60))
    _check("T02 4th request blocked", blocked is False)


def test_rate_limit_window_recovery():
    print("\n== rate_limit window recovery ==")
    reset_buckets()
    key = "k3"
    # window 1초 — 빠르게 한도 채우고 sleep 후 복구 확인.
    for _ in range(3):
        asyncio.run(check_and_record(key, max_requests=3, window_s=1))
    time.sleep(1.1)
    recovered = asyncio.run(check_and_record(key, max_requests=3, window_s=1))
    _check("T03 request after window passes", recovered is True)


def test_rate_limit_default_max():
    print("\n== rate_limit default constants ==")
    _check("T04 DEFAULT_MAX_REQUESTS == 3", DEFAULT_MAX_REQUESTS == 3)


def test_rate_limit_per_key_isolation():
    print("\n== rate_limit per-key isolation ==")
    reset_buckets()
    for _ in range(3):
        asyncio.run(check_and_record("ipA", max_requests=3, window_s=60))
    # ipA blocked, ipB still OK
    a = asyncio.run(check_and_record("ipA", max_requests=3, window_s=60))
    b = asyncio.run(check_and_record("ipB", max_requests=3, window_s=60))
    _check("T05 ipA blocked", a is False)
    _check("T06 ipB still passes", b is True)


def test_hash_ip_deterministic():
    print("\n== hash_ip deterministic ==")
    h1 = hash_ip("1.2.3.4", salt="s1")
    h2 = hash_ip("1.2.3.4", salt="s1")
    _check("T07 same ip+salt yields same hash", h1 == h2)
    _check("T08 sha256 hex length 64", len(h1) == 64)


def test_hash_ip_salt_changes_output():
    print("\n== hash_ip salt changes output ==")
    h1 = hash_ip("1.2.3.4", salt="s1")
    h2 = hash_ip("1.2.3.4", salt="s2")
    _check("T09 different salt → different hash", h1 != h2)


def test_reset_buckets_specific_key():
    print("\n== reset_buckets specific key ==")
    reset_buckets()
    asyncio.run(check_and_record("kx", max_requests=1, window_s=60))
    blocked = asyncio.run(check_and_record("kx", max_requests=1, window_s=60))
    _check("T10 kx blocked after 1", blocked is False)
    reset_buckets(["kx"])
    after = asyncio.run(check_and_record("kx", max_requests=1, window_s=60))
    _check("T11 kx allowed after reset", after is True)


# ─── schemas/contact ────────────────────────────────────────────────────

def test_contact_create_valid():
    print("\n== ContactCreate valid ==")
    payload = ContactCreate(
        name="Jane Doe",
        email="jane@example.com",
        company=" Acme  ",
        topic=ContactTopic.demo,
        message="Please show me a demo.",
        locale="ko",
    )
    _check("T12 name preserved", payload.name == "Jane Doe")
    _check("T13 company stripped", payload.company == "Acme")
    _check("T14 topic = demo", payload.topic is ContactTopic.demo)
    _check("T15 locale = ko", payload.locale == "ko")
    _check("T16 honeypot defaults to None", payload.website is None)


def test_contact_create_company_empty_to_none():
    print("\n== ContactCreate empty company → None ==")
    payload = ContactCreate(
        name="J", email="j@x.com", company="   ", message="hi",
    )
    _check("T17 whitespace-only company → None", payload.company is None)


def test_contact_create_topic_default():
    print("\n== ContactCreate topic default = general ==")
    payload = ContactCreate(name="J", email="j@x.com", message="hi")
    _check("T18 default topic = general", payload.topic is ContactTopic.general)


def test_contact_create_invalid_email():
    print("\n== ContactCreate invalid email ==")
    raised = False
    try:
        ContactCreate(name="J", email="not-an-email", message="hi")
    except Exception:
        raised = True
    _check("T19 invalid email raises", raised)


def test_contact_create_message_too_long():
    print("\n== ContactCreate message too long ==")
    raised = False
    try:
        ContactCreate(name="J", email="j@x.com", message="x" * 5001)
    except Exception:
        raised = True
    _check("T20 5001-char message raises", raised)


def test_contact_create_name_empty():
    print("\n== ContactCreate name empty ==")
    raised = False
    try:
        ContactCreate(name="   ", email="j@x.com", message="hi")
    except Exception:
        raised = True
    _check("T21 whitespace-only name raises", raised)


def test_contact_create_honeypot_passthrough():
    print("\n== ContactCreate honeypot passthrough ==")
    payload = ContactCreate(
        name="J", email="j@x.com", message="hi", website="http://bot.invalid",
    )
    _check("T22 honeypot string preserved for router check",
           payload.website == "http://bot.invalid")


# ─── routers/plans ──────────────────────────────────────────────────────

def test_plan_display_order_keys():
    print("\n== plan display order ==")
    _check("T23 free=0", _PLAN_DISPLAY_ORDER["free"] == 0)
    _check("T24 basic<pro", _PLAN_DISPLAY_ORDER["basic"] < _PLAN_DISPLAY_ORDER["pro"])
    _check("T25 pro<business",
           _PLAN_DISPLAY_ORDER["pro"] < _PLAN_DISPLAY_ORDER["business"])
    _check("T26 business<enterprise",
           _PLAN_DISPLAY_ORDER["business"] < _PLAN_DISPLAY_ORDER["enterprise"])


def test_plan_unknown_id_sorts_last():
    print("\n== plan unknown id sorts last ==")
    plans = [
        SimpleNamespace(id="custom"),
        SimpleNamespace(id="enterprise"),
        SimpleNamespace(id="free"),
    ]
    plans.sort(key=lambda p: _PLAN_DISPLAY_ORDER.get(p.id, 99))
    _check("T27 unknown 'custom' sorts after enterprise",
           plans[-1].id == "custom")
    _check("T28 free first", plans[0].id == "free")


# ─── email_service.send_contact_notification ────────────────────────────

def _make_settings(api_key: str = "", to: str = "hello@ahxov.com",
                   from_: str = "AEO Visibility <hello@ahxov.com>"):
    return SimpleNamespace(
        resend_api_key=api_key,
        contact_notification_to=to,
        resend_from_contact=from_,
    )


def test_contact_notification_no_api_key():
    print("\n== contact notification no api_key ==")
    sub = SimpleNamespace(
        name="J", email="j@x.com", company=None,
        topic=ContactTopic.demo, message="hi", locale="en", referrer_url=None,
    )
    with patch.object(svc, "get_settings", lambda: _make_settings(api_key="")):
        ok = asyncio.run(send_contact_notification(submission=sub, submission_id=uuid4()))
    _check("T29 api_key empty returns False", ok is False)


def test_contact_notification_to_empty():
    print("\n== contact notification to empty ==")
    sub = SimpleNamespace(
        name="J", email="j@x.com", company=None,
        topic=ContactTopic.demo, message="hi", locale="en", referrer_url=None,
    )
    with patch.object(svc, "get_settings",
                      lambda: _make_settings(api_key="re_x", to="")):
        ok = asyncio.run(send_contact_notification(submission=sub, submission_id=uuid4()))
    _check("T30 contact_notification_to empty returns False", ok is False)


def test_contact_notification_send_with_mock():
    print("\n== contact notification with mock ==")
    sub = SimpleNamespace(
        name="Jane", email="jane@example.com", company="Acme",
        topic=ContactTopic.sales, message="interested",
        locale="ko", referrer_url="https://x.com/pricing",
    )
    captured: dict = {}

    def fake_send_sync(payload):
        captured.update(payload)

    with patch.object(svc, "get_settings",
                      lambda: _make_settings(
                          api_key="re_x",
                          to="ops@a.com,sales@a.com",
                          from_="AEO Visibility <hello@ahxov.com>")), \
         patch.object(svc, "_resend_send_sync", side_effect=fake_send_sync):
        ok = asyncio.run(send_contact_notification(
            submission=sub, submission_id=UUID(int=1),
        ))

    _check("T31 send returns True", ok is True)
    _check("T32 from is hello@ahxov.com",
           captured.get("from") == "AEO Visibility <hello@ahxov.com>")
    _check("T33 subject mentions sales topic",
           "Sales" in (captured.get("subject") or ""))
    _check("T34 subject embeds name",
           "Jane" in (captured.get("subject") or ""))
    _check("T35 to is last recipient (sequential per-rcp send)",
           captured.get("to") == ["sales@a.com"])
    html = captured.get("html") or ""
    _check("T36 html contains email", "jane@example.com" in html)
    _check("T37 html contains message", "interested" in html)
    _check("T38 html contains submission_id",
           "00000000-0000-0000-0000-000000000001" in html)


def test_contact_notification_context_dict_input():
    print("\n== contact notification dict input ==")
    sub_dict = {
        "name": "Bob",
        "email": "bob@x.com",
        "company": None,
        "topic": ContactTopic.demo,
        "message": "demo plz",
        "locale": "es",
        "referrer_url": None,
    }
    ctx = build_contact_notification_context(
        submission=sub_dict, submission_id=UUID(int=2),
    )
    _check("T39 dict input — name", ctx["name"] == "Bob")
    _check("T40 None company → '—'", ctx["company"] == "—")
    _check("T41 None referrer → '—'", ctx["referrer_url"] == "—")
    _check("T42 topic enum → str", ctx["topic"] == "demo")
    _check("T43 submission_id stringified",
           ctx["submission_id"] == "00000000-0000-0000-0000-000000000002")


def test_contact_notification_context_string_topic():
    print("\n== contact notification context string topic ==")
    sub = SimpleNamespace(
        name="Z", email="z@x.com", company="X",
        topic="general", message="hi", locale="en", referrer_url=None,
    )
    ctx = build_contact_notification_context(
        submission=sub, submission_id=uuid4(),
    )
    _check("T44 string topic preserved", ctx["topic"] == "general")


def test_trigger_constant():
    print("\n== TRIGGER_CONTACT_NOTIFICATION constant ==")
    _check("T45 trigger key matches dir name",
           TRIGGER_CONTACT_NOTIFICATION == "contact_notification")


# ─── runner ─────────────────────────────────────────────────────────────

def main() -> int:
    test_rate_limit_within_quota()
    test_rate_limit_exceeds_quota()
    test_rate_limit_window_recovery()
    test_rate_limit_default_max()
    test_rate_limit_per_key_isolation()
    test_hash_ip_deterministic()
    test_hash_ip_salt_changes_output()
    test_reset_buckets_specific_key()

    test_contact_create_valid()
    test_contact_create_company_empty_to_none()
    test_contact_create_topic_default()
    test_contact_create_invalid_email()
    test_contact_create_message_too_long()
    test_contact_create_name_empty()
    test_contact_create_honeypot_passthrough()

    test_plan_display_order_keys()
    test_plan_unknown_id_sorts_last()

    test_contact_notification_no_api_key()
    test_contact_notification_to_empty()
    test_contact_notification_send_with_mock()
    test_contact_notification_context_dict_input()
    test_contact_notification_context_string_topic()
    test_trigger_constant()

    if FAILED:
        print(f"\n[FAIL] {len(FAILED)} cases failed:")
        for label in FAILED:
            print(f"  - {label}")
        return 1
    print(f"\n[PASS] all {45 - len(FAILED)} F3-pricing test cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
