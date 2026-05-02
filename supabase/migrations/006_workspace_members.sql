-- ============================================================
-- 006_workspace_members.sql
-- workspace_members: 워크스페이스 ↔ 사용자 N:M, role 포함.
-- workspace_role ENUM: owner / admin / member / viewer (SPEC §6-1).
-- workspace INSERT 시 owner row를 자동 생성하는 트리거 포함.
-- ============================================================
BEGIN;

CREATE TYPE workspace_role AS ENUM ('owner', 'admin', 'member', 'viewer');

CREATE TABLE workspace_members (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id       UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    role          workspace_role NOT NULL,
    invited_by    UUID REFERENCES profiles(id),
    joined_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (workspace_id, user_id)
);

CREATE INDEX idx_workspace_members_user ON workspace_members(user_id);
CREATE INDEX idx_workspace_members_workspace ON workspace_members(workspace_id);

-- ─── 워크스페이스 생성 시 owner 자동 등록 ───
-- workspaces.owner_id로 지정된 사용자를 workspace_members에 owner로 삽입.
-- SECURITY DEFINER로 RLS 우회 (workspace 생성자가 아직 멤버가 아니므로).
CREATE OR REPLACE FUNCTION public.add_owner_to_workspace_members()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO public.workspace_members (workspace_id, user_id, role)
    VALUES (NEW.id, NEW.owner_id, 'owner')
    ON CONFLICT (workspace_id, user_id) DO NOTHING;
    RETURN NEW;
END;
$$;

CREATE TRIGGER workspaces_add_owner_member
AFTER INSERT ON workspaces
FOR EACH ROW EXECUTE FUNCTION public.add_owner_to_workspace_members();

COMMIT;
