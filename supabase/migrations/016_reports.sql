-- ============================================================
-- 016_reports.sql
-- reports: PDF/CSV 다운로드 메타 (Phase 1 stub).
--
-- Phase 1 범위: 메타 + status 전이 + signed URL 발급용 골격.
-- 실 PDF/CSV 렌더 + Supabase Storage 업로드는 Phase 3.
--
-- 1 row = 사용자가 요청한 1 다운로드. ``analysis_id`` 가 set 되면 단일
-- 분석 결과 리포트, NULL 이면 워크스페이스 종합 리포트(향후).
--
-- status 전이:
--   pending  — POST /reports 직후 (BackgroundTask 큐).
--   ready    — 렌더 완료 + Supabase Storage 업로드 완료 (storage_path NOT NULL).
--   failed   — 렌더 실패 (error_message NOT NULL).
--
-- INSERT/UPDATE 는 라우터 / report_task(service_role) 전담. RLS SELECT 만 허용.
-- ============================================================
BEGIN;

-- ─── ENUM ───
CREATE TYPE report_format AS ENUM ('pdf', 'csv');
CREATE TYPE report_status AS ENUM ('pending', 'ready', 'failed');

-- ─── 테이블 ───
CREATE TABLE reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id)        ON DELETE CASCADE,
    -- 단일 분석 결과 리포트. NULL = 워크스페이스 종합 리포트 (Phase 3).
    -- 분석 row 가 삭제되어도 리포트 메타는 보존(SET NULL) — 사용자가 과거 다운로드
    -- 를 추적할 수 있도록.
    analysis_id     UUID REFERENCES analysis_results(id)           ON DELETE SET NULL,
    format          report_format NOT NULL,
    status          report_status NOT NULL DEFAULT 'pending',
    -- Supabase Storage path 'reports/<workspace_id>/<report_id>.<format>'.
    -- Phase 1 stub: report_task 가 placeholder path 만 set, 실제 객체는 ❌.
    storage_path    TEXT,
    file_size_bytes BIGINT,
    requested_by    UUID NOT NULL REFERENCES profiles(id),
    requested_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- status 별 invariant: ready 면 path+completed 필수, failed 면 error+completed 필수.
    CONSTRAINT reports_status_invariants CHECK (
        (status = 'ready'   AND storage_path  IS NOT NULL AND completed_at IS NOT NULL) OR
        (status = 'failed'  AND error_message IS NOT NULL AND completed_at IS NOT NULL) OR
        (status = 'pending' AND completed_at  IS NULL)
    ),

    CONSTRAINT reports_size_nonneg CHECK (
        file_size_bytes IS NULL OR file_size_bytes >= 0
    )
);

-- ─── 인덱스 ───
-- 워크스페이스 단위 목록 (최신순).
CREATE INDEX idx_reports_workspace_time
    ON reports(workspace_id, requested_at DESC);

-- 분석 ID 역참조 (특정 분석의 리포트 history).
CREATE INDEX idx_reports_analysis
    ON reports(analysis_id)
    WHERE analysis_id IS NOT NULL;

-- 큐 워커용 — pending 상태 탐색 (Phase 3 BackgroundTasks 또는 cron).
CREATE INDEX idx_reports_pending_workspace
    ON reports(workspace_id, requested_at)
    WHERE status = 'pending';

-- updated_at 자동 갱신 (005_workspaces 에서 정의된 set_updated_at 재사용).
CREATE TRIGGER reports_set_updated_at
BEFORE UPDATE ON reports
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================
-- RLS — 멤버 SELECT 만, 쓰기는 라우터 / report_task(service_role) 전담.
-- ============================================================
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY reports_select ON reports FOR SELECT
    TO authenticated
    USING (workspace_id IN (SELECT public.user_workspace_ids(auth.uid())));

-- INSERT/UPDATE/DELETE 정책 부재 = authenticated 일반 사용자 차단.
-- report_task / 라우터는 service_role 또는 직접 connection 으로 RLS 우회.

COMMIT;
