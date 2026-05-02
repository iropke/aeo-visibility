-- ============================================================
-- 005_workspaces.sql
-- workspaces: 회사/조직 단위. 모든 도메인 데이터의 격리 단위.
-- SPEC §5-2 workspaces 준수.
-- 멤버 추가 트리거는 006에서 (workspace_members 테이블 생성 후).
-- ============================================================
BEGIN;

CREATE TABLE workspaces (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                  TEXT NOT NULL,
    slug                  TEXT UNIQUE NOT NULL,
    primary_language      TEXT NOT NULL DEFAULT 'en'
                              CHECK (primary_language IN ('en', 'ko', 'es')),
    timezone              TEXT NOT NULL DEFAULT 'UTC',
    owner_id              UUID NOT NULL REFERENCES profiles(id),
    plan_id               TEXT NOT NULL REFERENCES plans(id) DEFAULT 'free',
    stripe_customer_id    TEXT,
    delete_requested_at   TIMESTAMPTZ,
    delete_grace_until    TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_workspaces_owner ON workspaces(owner_id);
CREATE INDEX idx_workspaces_delete_grace ON workspaces(delete_grace_until)
    WHERE delete_grace_until IS NOT NULL;

CREATE TRIGGER workspaces_set_updated_at
BEFORE UPDATE ON workspaces
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

COMMIT;
