"""Phase 1 E2E validation script.

Validates:
  1. Supabase Admin API user creation triggers handle_new_user (profiles row created)
  2. Backend JWT verification accepts the issued access_token
  3. POST /api/workspaces creates a workspace AND triggers add_owner_to_workspace_members
  4. POST /api/workspaces ALSO triggers start_trial_for_new_workspace (subscriptions row)
  5. GET /api/workspaces returns the new workspace
  6. RLS isolation: a second user does NOT see the first user's workspace
  7. Sites CRUD enforcement on free plan (max_sites=1, competitors_per_site=0,
     soft delete + 30-day cooldown)

Run from backend/ with .venv active:
    python scripts/e2e_phase1.py
"""
from __future__ import annotations

import asyncio
import secrets
import sys
import uuid

import httpx

from app.config import get_settings


SETTINGS = get_settings()
SUPABASE_URL = SETTINGS.supabase_url.rstrip("/")
SERVICE_ROLE = SETTINGS.supabase_service_role_key
ANON_KEY = SETTINGS.supabase_anon_key
BACKEND_URL = "http://127.0.0.1:8000"


def banner(msg: str) -> None:
    print(f"\n{'='*60}\n{msg}\n{'='*60}")


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


async def admin_create_user(client: httpx.AsyncClient, email: str, password: str) -> dict:
    r = await client.post(
        f"{SUPABASE_URL}/auth/v1/admin/users",
        headers={
            "apikey": SERVICE_ROLE,
            "Authorization": f"Bearer {SERVICE_ROLE}",
            "Content-Type": "application/json",
        },
        json={
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"display_name": email.split("@")[0]},
        },
    )
    if r.status_code not in (200, 201):
        fail(f"admin create user: {r.status_code} {r.text}")
    return r.json()


async def password_signin(client: httpx.AsyncClient, email: str, password: str) -> str:
    r = await client.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": ANON_KEY, "Content-Type": "application/json"},
        json={"email": email, "password": password},
    )
    if r.status_code != 200:
        fail(f"password signin: {r.status_code} {r.text}")
    return r.json()["access_token"]


async def admin_delete_user(client: httpx.AsyncClient, user_id: str) -> None:
    r = await client.delete(
        f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
        headers={"apikey": SERVICE_ROLE, "Authorization": f"Bearer {SERVICE_ROLE}"},
    )
    if r.status_code not in (200, 204):
        print(f"  cleanup user {user_id}: {r.status_code}")


async def main() -> None:
    suffix = secrets.token_hex(4)
    email_a = f"e2e-a-{suffix}@example.com"
    email_b = f"e2e-b-{suffix}@example.com"
    password = "Test12345!"

    user_a_id: str | None = None
    user_b_id: str | None = None

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            banner("Step 1: Create User A via Admin API")
            ua = await admin_create_user(client, email_a, password)
            user_a_id = ua["id"]
            ok(f"user A created: id={user_a_id}, email={email_a}")

            banner("Step 2: Verify handle_new_user trigger created profiles row")
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_a_id}",
                headers={
                    "apikey": SERVICE_ROLE,
                    "Authorization": f"Bearer {SERVICE_ROLE}",
                },
            )
            if r.status_code != 200:
                fail(f"profiles read: {r.status_code} {r.text}")
            rows = r.json()
            if len(rows) != 1:
                fail(f"expected 1 profiles row for user A, got {len(rows)}")
            ok(f"profiles row exists: display_name={rows[0].get('display_name')}, lang={rows[0].get('preferred_language')}")

            banner("Step 3: Sign in as User A → get JWT")
            token_a = await password_signin(client, email_a, password)
            ok(f"got access_token (len={len(token_a)})")

            banner("Step 4: Backend rejects requests without JWT")
            r = await client.get(f"{BACKEND_URL}/api/workspaces")
            if r.status_code != 401:
                fail(f"expected 401, got {r.status_code}")
            ok("401 Unauthorized as expected")

            banner("Step 5: User A creates a workspace via backend")
            r = await client.post(
                f"{BACKEND_URL}/api/workspaces",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"name": f"E2E Workspace {suffix}", "primary_language": "ko", "timezone": "Asia/Seoul"},
            )
            if r.status_code != 201:
                fail(f"create workspace: {r.status_code} {r.text}")
            ws_a = r.json()
            ok(f"workspace created: id={ws_a['id']}, slug={ws_a['slug']}, role={ws_a['role']}")
            if ws_a["role"] != "owner":
                fail(f"expected role=owner, got {ws_a['role']}")

            banner("Step 6: Verify add_owner_to_workspace_members trigger fired")
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/workspace_members?workspace_id=eq.{ws_a['id']}",
                headers={
                    "apikey": SERVICE_ROLE,
                    "Authorization": f"Bearer {SERVICE_ROLE}",
                },
            )
            members = r.json()
            if len(members) != 1:
                fail(f"expected 1 workspace_members row, got {len(members)}")
            if members[0]["user_id"] != user_a_id or members[0]["role"] != "owner":
                fail(f"unexpected member row: {members[0]}")
            ok("trigger created owner member row")

            banner("Step 6b: Verify start_trial_for_new_workspace trigger fired (7-day trial)")
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/subscriptions?workspace_id=eq.{ws_a['id']}",
                headers={
                    "apikey": SERVICE_ROLE,
                    "Authorization": f"Bearer {SERVICE_ROLE}",
                },
            )
            subs = r.json()
            if len(subs) != 1:
                fail(f"expected 1 subscriptions row, got {len(subs)}")
            sub = subs[0]
            if sub["status"] != "trial":
                fail(f"expected status=trial, got {sub['status']}")
            if sub["plan_id"] != "free":
                fail(f"expected plan_id=free, got {sub['plan_id']}")
            if sub["billing_cycle"] != "monthly":
                fail(f"expected billing_cycle=monthly, got {sub['billing_cycle']}")
            if not sub.get("trial_ends_at"):
                fail("expected trial_ends_at to be set")
            ok(f"trial subscription auto-created: status={sub['status']}, plan={sub['plan_id']}, trial_ends_at={sub['trial_ends_at']}")

            banner("Step 7: User A lists their workspaces")
            r = await client.get(
                f"{BACKEND_URL}/api/workspaces",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            if r.status_code != 200:
                fail(f"list workspaces: {r.status_code} {r.text}")
            wss = r.json()
            if not any(ws["id"] == ws_a["id"] for ws in wss):
                fail(f"new workspace not in list: {wss}")
            ok(f"User A sees {len(wss)} workspace(s) including the new one")

            banner("Step 8: Create User B and verify RLS isolation")
            ub = await admin_create_user(client, email_b, password)
            user_b_id = ub["id"]
            token_b = await password_signin(client, email_b, password)
            r = await client.get(
                f"{BACKEND_URL}/api/workspaces",
                headers={"Authorization": f"Bearer {token_b}"},
            )
            if r.status_code != 200:
                fail(f"list workspaces (B): {r.status_code} {r.text}")
            wss_b = r.json()
            if any(ws["id"] == ws_a["id"] for ws in wss_b):
                fail(f"RLS LEAK: User B sees User A's workspace! got {wss_b}")
            ok(f"User B sees {len(wss_b)} workspace(s) — RLS isolation confirmed")

            banner("Step 9: User B cannot fetch User A's workspace by id")
            r = await client.get(
                f"{BACKEND_URL}/api/workspaces/{ws_a['id']}",
                headers={"Authorization": f"Bearer {token_b}"},
            )
            if r.status_code not in (403, 404):
                fail(f"expected 403/404 for cross-user fetch, got {r.status_code} {r.text}")
            ok(f"cross-user fetch blocked: {r.status_code}")

            banner("Step 9b: User A creates an own site (free plan max_sites=1)")
            r = await client.post(
                f"{BACKEND_URL}/api/workspaces/{ws_a['id']}/sites",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"url": "https://example.com", "type": "own"},
            )
            if r.status_code != 201:
                fail(f"create site: {r.status_code} {r.text}")
            site_a = r.json()
            ok(f"own site created: id={site_a['id']}, domain={site_a['domain']}")

            banner("Step 9c: 2nd own site blocked by free plan max_sites=1")
            r = await client.post(
                f"{BACKEND_URL}/api/workspaces/{ws_a['id']}/sites",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"url": "https://other.com", "type": "own"},
            )
            if r.status_code != 403:
                fail(f"expected 403 for 2nd own site, got {r.status_code} {r.text}")
            ok("2nd own site blocked by max_sites limit")

            banner("Step 9d: Competitor site blocked by free plan competitors_per_site=0")
            r = await client.post(
                f"{BACKEND_URL}/api/workspaces/{ws_a['id']}/sites",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"url": "https://competitor.com", "type": "competitor"},
            )
            if r.status_code != 403:
                fail(f"expected 403 for competitor on free plan, got {r.status_code} {r.text}")
            ok("competitor site blocked by competitors_per_site=0 limit")

            banner("Step 9e: List sites returns 1 active site")
            r = await client.get(
                f"{BACKEND_URL}/api/workspaces/{ws_a['id']}/sites",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            if r.status_code != 200:
                fail(f"list sites: {r.status_code} {r.text}")
            sites_list = r.json()
            if len(sites_list) != 1 or sites_list[0]["id"] != site_a["id"]:
                fail(f"unexpected site list: {sites_list}")
            ok("list sites returns 1 active site")

            banner("Step 9f: Soft delete site (deleted_at + delete_cooldown_until set)")
            r = await client.delete(
                f"{BACKEND_URL}/api/workspaces/{ws_a['id']}/sites/{site_a['id']}",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            if r.status_code != 204:
                fail(f"delete site: {r.status_code} {r.text}")
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/sites?id=eq.{site_a['id']}",
                headers={"apikey": SERVICE_ROLE, "Authorization": f"Bearer {SERVICE_ROLE}"},
            )
            rows = r.json()
            if not rows or not rows[0].get("deleted_at") or not rows[0].get("delete_cooldown_until"):
                fail(f"expected soft-deleted row with deleted_at + delete_cooldown_until, got {rows}")
            ok(f"site soft-deleted: deleted_at set, cooldown_until={rows[0]['delete_cooldown_until']}")

            banner("Step 9g: Re-creating same domain blocked by 30-day cooldown (409)")
            r = await client.post(
                f"{BACKEND_URL}/api/workspaces/{ws_a['id']}/sites",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"url": "https://example.com", "type": "own"},
            )
            if r.status_code != 409:
                fail(f"expected 409 cooldown, got {r.status_code} {r.text}")
            ok("re-creation of same domain blocked (30-day cooldown)")

            banner("Step 10: User A deletes the workspace")
            r = await client.delete(
                f"{BACKEND_URL}/api/workspaces/{ws_a['id']}",
                headers={"Authorization": f"Bearer {token_a}"},
            )
            if r.status_code != 204:
                fail(f"delete workspace: {r.status_code} {r.text}")
            ok("workspace deleted (204)")

            banner("ALL CHECKS PASSED")

        finally:
            banner("Cleanup: delete test users")
            if user_a_id:
                await admin_delete_user(client, user_a_id)
            if user_b_id:
                await admin_delete_user(client, user_b_id)


if __name__ == "__main__":
    asyncio.run(main())
