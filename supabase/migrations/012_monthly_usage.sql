-- ============================================================
-- 012_monthly_usage.sql
-- monthly_usage: 워크스페이스 × YYYY-MM 단위 월간 사용량 카운터.
--
-- SPEC §5 monthly_usage 정합 + 메모리 의도(funding source 분리):
--   custom_analyses_used 를 4개로 분리:
--     - base_analyses_used         — plans.custom_analyses_per_month 차감
--     - basic_pack_analyses_used   — custom_pack_basic addon (+5/월) 차감
--     - pro_pack_analyses_used     — custom_pack_pro addon (+20/월) 차감
--     - payg_analyses_used         — payg_custom (단건 PAYG) 사용 횟수
--
-- 기타 카운터:
--   - sites_changed_count — 1회/월 URL 교체 enforce용 (현재 sites 라우터는
--     sites.last_url_changed_at 기반이지만 G3 이후 정합 정리 예정)
--   - qa_messages_count   — Phase 1 mock UI 이후 실제 사용 시 enforce
--
-- auto_run_completed_at — 매월 cron 멱등성 (한 워크스페이스 × 한 달 = 1회).
--
-- INSERT/UPDATE는 usage_service / 분석 task / cron(service_role) 전담.
-- 일반 사용자는 자기 워크스페이스 SELECT만 (잔여 횟수 표시용).
-- ============================================================
BEGIN;

CREATE TABLE monthly_usage (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id                UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    year_month                  TEXT NOT NULL,                      -- 'YYYY-MM'
    base_analyses_used          INT  NOT NULL DEFAULT 0,
    basic_pack_analyses_used    INT  NOT NULL DEFAULT 0,
    pro_pack_analyses_used      INT  NOT NULL DEFAULT 0,
    payg_analyses_used          INT  NOT NULL DEFAULT 0,
    sites_changed_count         INT  NOT NULL DEFAULT 0,
    qa_messages_count           INT  NOT NULL DEFAULT 0,
    auto_run_completed_at       TIMESTAMPTZ,                        -- 매월 cron 멱등성
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- year_month 형식 'YYYY-MM' (01~12).
    CONSTRAINT monthly_usage_year_month_format CHECK (
        year_month ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'
    ),
    CONSTRAINT monthly_usage_base_nonneg          CHECK (base_analyses_used        >= 0),
    CONSTRAINT monthly_usage_basic_pack_nonneg    CHECK (basic_pack_analyses_used  >= 0),
    CONSTRAINT monthly_usage_pro_pack_nonneg      CHECK (pro_pack_analyses_used    >= 0),
    CONSTRAINT monthly_usage_payg_nonneg          CHECK (payg_analyses_used        >= 0),
    CONSTRAINT monthly_usage_sites_changed_nonneg CHECK (sites_changed_count       >= 0),
    CONSTRAINT monthly_usage_qa_nonneg            CHECK (qa_messages_count         >= 0)
);

-- 워크스페이스 × 월 UNIQUE (upsert 키).
CREATE UNIQUE INDEX uniq_monthly_usage_workspace_month
    ON monthly_usage(workspace_id, year_month);

-- 자기 워크스페이스 잔여 카운터 조회용 (워크스페이스 단위 조회 패턴).
CREATE INDEX idx_monthly_usage_workspace
    ON monthly_usage(workspace_id);

CREATE TRIGGER monthly_usage_set_updated_at
BEFORE UPDATE ON monthly_usage
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================
-- RLS — 멤버 SELECT만, 쓰기는 service_role(usage_service / 분석 task / cron) 전담.
-- ============================================================
ALTER TABLE monthly_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY monthly_usage_select ON monthly_usage FOR SELECT
    TO authenticated
    USING (workspace_id IN (SELECT public.user_workspace_ids(auth.uid())));

-- INSERT/UPDATE/DELETE 정책 부재 = authenticated 일반 사용자 차단.

COMMIT;
