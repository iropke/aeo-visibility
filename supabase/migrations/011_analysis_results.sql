-- ============================================================
-- 011_analysis_results.sql
-- analysis_results: 5축 분석 결과 저장 (1 row = 1 분석 실행).
--
-- SPEC §5 analysis_results + §7 분석 엔진 정합:
--   - trigger_type = 'auto' (매월 cron) | 'manual' (사용자 트리거)
--   - funding_source = 'auto' | 'base' | 'basic_pack' | 'pro_pack' | 'payg'
--       * auto         — 매월 cron, 차감 ❌
--       * base         — 워크스페이스 plan의 custom_analyses_per_month 차감
--       * basic_pack   — custom_pack_basic addon (+5/월) 차감
--       * pro_pack     — custom_pack_pro addon (+20/월) 차감
--       * payg         — payg_custom (단건 PAYG, $2.99/회)
--   - 차감 우선순위(라우터): pro_pack → basic_pack → base → payg (G3에서 구현)
--
-- categories[] 는 부분 분석(Custom Re-analyze) 시 선택된 카테고리만 (SPEC §7-5).
-- raw_metrics / category_scores / insights / improvements 는 §7-2 표준 스키마.
--
-- INSERT/UPDATE는 BackgroundTasks(service_role) 전담. 일반 사용자는 SELECT만.
-- 사이트 hard delete (Phase 2 grace_processor) 시 CASCADE 로 함께 삭제.
-- ============================================================
BEGIN;

-- ─── ENUM ───
CREATE TYPE analysis_trigger_type  AS ENUM ('auto', 'manual');

CREATE TYPE analysis_funding_source AS ENUM
    ('auto', 'base', 'basic_pack', 'pro_pack', 'payg');

CREATE TYPE analysis_status AS ENUM
    ('queued', 'running', 'completed', 'failed');

-- ─── 테이블 ───
CREATE TABLE analysis_results (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id       UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    site_id            UUID NOT NULL REFERENCES sites(id)      ON DELETE CASCADE,
    trigger_type       analysis_trigger_type    NOT NULL,
    funding_source     analysis_funding_source  NOT NULL,
    triggered_by       UUID REFERENCES profiles(id),  -- NULL for auto
    triggered_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at       TIMESTAMPTZ,
    duration_ms        INT,
    categories         TEXT[] NOT NULL,
    overall_score      NUMERIC(5, 2),
    category_scores    JSONB,
    raw_metrics        JSONB,
    insights           JSONB,
    improvements       JSONB,
    analysis_version   TEXT NOT NULL,
    status             analysis_status NOT NULL DEFAULT 'queued',
    error_message      TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- trigger_type/funding_source 일관성: auto cron이 차감을 가질 수 없고,
    -- manual 트리거는 'auto' funding을 가질 수 없음.
    CONSTRAINT analysis_results_trigger_funding_consistency CHECK (
        (trigger_type = 'auto'   AND funding_source = 'auto') OR
        (trigger_type = 'manual' AND funding_source <> 'auto')
    ),

    -- categories 비어있지 않음 (Custom 분석은 최소 1개, full은 5개).
    CONSTRAINT analysis_results_categories_not_empty CHECK (
        cardinality(categories) >= 1
    ),

    -- overall_score 0~100 (NULL 허용 — 분석 완료 전).
    CONSTRAINT analysis_results_overall_score_range CHECK (
        overall_score IS NULL OR (overall_score >= 0 AND overall_score <= 100)
    ),

    -- duration_ms 양수.
    CONSTRAINT analysis_results_duration_nonneg CHECK (
        duration_ms IS NULL OR duration_ms >= 0
    )
);

-- ─── 인덱스 ───
-- 시계열 차트 (사이트별, 최신순). SPEC §5 명시 인덱스.
CREATE INDEX idx_analysis_results_site_time
    ON analysis_results(site_id, triggered_at DESC);

-- 워크스페이스 단위 조회 (대시보드, 카운트).
CREATE INDEX idx_analysis_results_workspace
    ON analysis_results(workspace_id);

-- 큐/러너용 — queued/running 상태 탐색.
CREATE INDEX idx_analysis_results_active_status
    ON analysis_results(status, triggered_at)
    WHERE status IN ('queued', 'running');

-- 매월 자동 분석 멱등성 — workspace × month별 auto 1건 검사용 partial index.
-- (실제 멱등성은 monthly_usage.auto_run_completed_at 보조 사용)
CREATE INDEX idx_analysis_results_workspace_month_auto
    ON analysis_results(workspace_id, triggered_at DESC)
    WHERE trigger_type = 'auto';

-- ============================================================
-- RLS — 멤버 SELECT만, 쓰기는 BackgroundTasks(service_role)만.
-- viewer 분석 트리거 차단은 라우터 레벨에서 (G3에서 행위 단위 가드).
-- ============================================================
ALTER TABLE analysis_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY analysis_results_select ON analysis_results FOR SELECT
    TO authenticated
    USING (workspace_id IN (SELECT public.user_workspace_ids(auth.uid())));

-- INSERT/UPDATE/DELETE 정책 부재 = authenticated 일반 사용자 차단.
-- 분석 task 는 service_role 키로 RLS 우회.

COMMIT;
