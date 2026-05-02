-- ============================================================
-- 010_sites.sql
-- sites: 워크스페이스가 분석할 자사 / 경쟁사 사이트.
--
-- SPEC §5-2 sites + §4-5 어뷰징 방지 정합:
--   - 사이트 변경 (URL 교체): 워크스페이스당 월 1회 (첫 분석 전은 미차감) — 라우터에서 enforce
--   - 사이트 삭제 cooldown: 동일 도메인 재등록 30일 차단 — soft delete로 처리
--   - 동일 워크스페이스 내 동일 도메인 활성 사이트는 1건만 허용 (UNIQUE partial index)
--
-- Soft delete 모델: DELETE 라우터는 INSERT/UPDATE 형태로 deleted_at + delete_cooldown_until만 set.
-- 30일 후 application 또는 향후 grace_processor가 hard delete (또는 cooldown 만료).
--
-- max_sites / competitors_per_site 한도는 plans 테이블 컬럼값으로 라우터에서 enforce.
-- ============================================================
BEGIN;

CREATE TYPE site_type AS ENUM ('own', 'competitor');

CREATE TABLE sites (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id             UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    url                      TEXT NOT NULL,
    domain                   TEXT NOT NULL,        -- 정규화된 도메인 (host, lowercase, www. 제거)
    nickname                 TEXT,
    type                     site_type NOT NULL DEFAULT 'own',
    last_analyzed_at         TIMESTAMPTZ,          -- 분석 완료 시 갱신 (분석 라우터에서)
    last_url_changed_at      TIMESTAMPTZ,          -- URL 교체 시 갱신 (1회/월 제약 검사용)
    deleted_at               TIMESTAMPTZ,          -- soft delete 시점
    delete_cooldown_until    TIMESTAMPTZ,          -- 동일 도메인 재등록 차단 만료 시점
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 활성 사이트 목록/카운트 (type별).
CREATE INDEX idx_sites_workspace_active ON sites(workspace_id, type)
    WHERE deleted_at IS NULL;

-- 30일 cooldown 검사 (soft-deleted but within cooldown window).
CREATE INDEX idx_sites_domain_cooldown ON sites(workspace_id, domain)
    WHERE delete_cooldown_until IS NOT NULL;

-- 워크스페이스 단위 1회/월 URL 교체 검사용.
CREATE INDEX idx_sites_workspace_url_change ON sites(workspace_id, last_url_changed_at)
    WHERE deleted_at IS NULL AND last_url_changed_at IS NOT NULL;

-- 동일 워크스페이스 내 동일 도메인 활성 사이트는 1건만.
CREATE UNIQUE INDEX uniq_sites_workspace_domain_active
    ON sites(workspace_id, domain)
    WHERE deleted_at IS NULL;

CREATE TRIGGER sites_set_updated_at
BEFORE UPDATE ON sites
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================
-- RLS — 멤버 SELECT, member+ INSERT/UPDATE, owner/admin DELETE.
-- (라우터는 일반적으로 soft delete를 UPDATE로 처리하므로 DELETE 정책은 hard delete 안전망용.)
-- ============================================================
ALTER TABLE sites ENABLE ROW LEVEL SECURITY;

CREATE POLICY sites_select ON sites FOR SELECT
    TO authenticated
    USING (workspace_id IN (SELECT public.user_workspace_ids(auth.uid())));

CREATE POLICY sites_insert_member_plus ON sites FOR INSERT
    TO authenticated
    WITH CHECK (
        public.user_workspace_role(auth.uid(), workspace_id)
            IN ('owner', 'admin', 'member')
    );

CREATE POLICY sites_update_member_plus ON sites FOR UPDATE
    TO authenticated
    USING (
        public.user_workspace_role(auth.uid(), workspace_id)
            IN ('owner', 'admin', 'member')
    )
    WITH CHECK (
        public.user_workspace_role(auth.uid(), workspace_id)
            IN ('owner', 'admin', 'member')
    );

CREATE POLICY sites_delete_admin ON sites FOR DELETE
    TO authenticated
    USING (
        public.user_workspace_role(auth.uid(), workspace_id)
            IN ('owner', 'admin')
    );

COMMIT;
