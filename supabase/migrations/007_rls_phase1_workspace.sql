-- ============================================================
-- 007_rls_phase1_workspace.sql
-- RLS 정책 — Phase 1 청크 A: profiles, plans, workspaces, workspace_members.
-- 이후 청크에서 sites/analysis_results 등 추가 테이블에 별도 마이그레이션으로 RLS 추가.
--
-- DEV_SPEC §8-2 패턴 + workspace_members 자기참조 무한루프 회피용
-- SECURITY DEFINER 헬퍼 함수 사용.
-- ============================================================
BEGIN;

-- ============================================================
-- 헬퍼 함수: SECURITY DEFINER로 RLS 우회하여 멤버십/역할 조회.
-- workspace_members의 정책이 workspace_members를 다시 SELECT 하면 무한 재귀.
-- 이 함수들은 workspace_members 정책이 호출 가능하도록 RLS를 우회.
-- ============================================================

-- 사용자가 멤버로 속한 워크스페이스 ID 목록.
CREATE OR REPLACE FUNCTION public.user_workspace_ids(uid UUID)
RETURNS SETOF UUID
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
    SELECT workspace_id FROM public.workspace_members WHERE user_id = uid;
$$;

-- 특정 워크스페이스에서 사용자의 역할 (없으면 NULL).
CREATE OR REPLACE FUNCTION public.user_workspace_role(uid UUID, ws UUID)
RETURNS workspace_role
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
    SELECT role FROM public.workspace_members
    WHERE user_id = uid AND workspace_id = ws
    LIMIT 1;
$$;

-- ============================================================
-- profiles
-- ============================================================
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- 본인 프로필 조회.
CREATE POLICY profiles_select_self ON profiles FOR SELECT
    TO authenticated
    USING (id = auth.uid());

-- 동일 워크스페이스 멤버 프로필 조회 (멤버 리스트 표시).
CREATE POLICY profiles_select_workspace_peer ON profiles FOR SELECT
    TO authenticated
    USING (
        id IN (
            SELECT user_id FROM workspace_members
            WHERE workspace_id IN (SELECT public.user_workspace_ids(auth.uid()))
        )
    );

-- 본인 프로필 수정.
CREATE POLICY profiles_update_self ON profiles FOR UPDATE
    TO authenticated
    USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

-- INSERT: handle_new_user 트리거(SECURITY DEFINER)만 허용 → policy 부재 = 일반 INSERT 차단.
-- DELETE: auth.users CASCADE로만 → policy 부재 = 일반 DELETE 차단.

-- ============================================================
-- plans (공개 마스터 데이터)
-- ============================================================
ALTER TABLE plans ENABLE ROW LEVEL SECURITY;

-- 누구나 활성 플랜 조회 (가격표).
CREATE POLICY plans_select_active ON plans FOR SELECT
    TO anon, authenticated
    USING (is_active = TRUE);

-- INSERT/UPDATE/DELETE: service_role(Admin)만 → policy 부재 = 차단.

-- ============================================================
-- workspaces
-- ============================================================
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;

-- 멤버인 워크스페이스만 조회.
CREATE POLICY workspaces_select ON workspaces FOR SELECT
    TO authenticated
    USING (id IN (SELECT public.user_workspace_ids(auth.uid())));

-- 본인을 owner로 한 워크스페이스 생성 가능.
-- (owner row는 add_owner_to_workspace_members 트리거가 자동 생성)
CREATE POLICY workspaces_insert_self_owner ON workspaces FOR INSERT
    TO authenticated
    WITH CHECK (owner_id = auth.uid());

-- owner/admin만 수정.
CREATE POLICY workspaces_update_owner_admin ON workspaces FOR UPDATE
    TO authenticated
    USING (public.user_workspace_role(auth.uid(), id) IN ('owner', 'admin'))
    WITH CHECK (public.user_workspace_role(auth.uid(), id) IN ('owner', 'admin'));

-- owner만 삭제 가능 (실제는 grace queue 통해 7일 후 — 별도 처리).
CREATE POLICY workspaces_delete_owner ON workspaces FOR DELETE
    TO authenticated
    USING (public.user_workspace_role(auth.uid(), id) = 'owner');

-- ============================================================
-- workspace_members
-- ============================================================
ALTER TABLE workspace_members ENABLE ROW LEVEL SECURITY;

-- 동일 워크스페이스 멤버 목록 조회.
CREATE POLICY members_select ON workspace_members FOR SELECT
    TO authenticated
    USING (workspace_id IN (SELECT public.user_workspace_ids(auth.uid())));

-- owner/admin이 신규 멤버 추가 가능.
-- (워크스페이스 최초 owner row는 트리거가 SECURITY DEFINER로 처리)
CREATE POLICY members_insert_owner_admin ON workspace_members FOR INSERT
    TO authenticated
    WITH CHECK (public.user_workspace_role(auth.uid(), workspace_id) IN ('owner', 'admin'));

-- owner만 role 변경 가능 (이양/강등).
CREATE POLICY members_update_owner ON workspace_members FOR UPDATE
    TO authenticated
    USING (public.user_workspace_role(auth.uid(), workspace_id) = 'owner')
    WITH CHECK (public.user_workspace_role(auth.uid(), workspace_id) = 'owner');

-- owner/admin이 멤버 제거 가능, 또는 본인이 워크스페이스 떠나기.
CREATE POLICY members_delete ON workspace_members FOR DELETE
    TO authenticated
    USING (
        public.user_workspace_role(auth.uid(), workspace_id) IN ('owner', 'admin')
        OR user_id = auth.uid()
    );

COMMIT;
