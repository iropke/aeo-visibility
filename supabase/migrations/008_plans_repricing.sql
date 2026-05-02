-- ============================================================
-- 008_plans_repricing.sql
-- 2026-05-02 시장조사 결과로 가격 정책 확정.
--
-- 변경 요약:
--   1. plans 테이블에 7개 컬럼 추가
--      (default_ai_engines, competitors_per_site, industry_benchmark,
--       audit_log_days, data_retention_years, support_tier, is_enterprise)
--   2. 5-tier (free/basic/medium/pro/premium) → 4-tier + Free trial + Enterprise
--      - 'medium', 'premium' 시드 DELETE (사용처 없음 — E2E 후 정리됨)
--      - 'free', 'basic', 'pro' 시드 가격/한도 UPDATE
--      - 'business', 'enterprise' 신규 INSERT
--   3. workspaces.plan_id 디폴트('free')는 7-day trial 의미로 그대로 유지.
--      trial 한도 enforce는 plans('free') row 값 자체로 충분 (별도 분기 ❌).
--      trial 만료/카운트다운은 추후 008_subscriptions에서 status='trial' +
--      trial_ends_at 으로 표현.
--
-- 관련 docs: SPEC §4 / reboot-service-concept §1
-- ============================================================
BEGIN;

-- ─── 1. 컬럼 추가 ───
ALTER TABLE plans
    ADD COLUMN default_ai_engines    INT     NOT NULL DEFAULT 3,
    ADD COLUMN competitors_per_site  INT     NOT NULL DEFAULT 0,
    ADD COLUMN industry_benchmark    BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN audit_log_days        INT     NOT NULL DEFAULT 0,
    ADD COLUMN data_retention_years  INT     NOT NULL DEFAULT 5,
    ADD COLUMN support_tier          TEXT    NOT NULL DEFAULT 'self'
        CHECK (support_tier IN ('self','email','email_chat','email_chat_sla4h','dedicated')),
    ADD COLUMN is_enterprise         BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN plans.default_ai_engines   IS '기본 AI 엔진 수. -1 = 무제한 (Enterprise)';
COMMENT ON COLUMN plans.competitors_per_site IS '자사 사이트당 경쟁사 한도. -1 = 무제한';
COMMENT ON COLUMN plans.industry_benchmark   IS 'Business 이상에서 산업 벤치마크 페이지 노출';
COMMENT ON COLUMN plans.audit_log_days       IS '감사 로그 보관 일수. 0 = 미제공, -1 = 무제한';
COMMENT ON COLUMN plans.data_retention_years IS '분석 결과 활성 보관 연수. 만료 후 1년 grace 별도';
COMMENT ON COLUMN plans.support_tier         IS '지원 채널 등급 (self/email/email_chat/email_chat_sla4h/dedicated)';
COMMENT ON COLUMN plans.is_enterprise        IS 'Enterprise 표시 (annual commit 강제, wire transfer 가능)';

-- ─── 2. 옛 시드 정리 ───
-- workspaces.plan_id FK 참조 row가 없는 경우에만 안전 (E2E 후 정리됨).
DELETE FROM plans WHERE id IN ('medium', 'premium');

-- ─── 3. 기존 시드 UPDATE ───
-- free = 7-day trial 한도 (보수적: 자사 1 / 경쟁사 0 / 멤버 1 / Custom 0).
UPDATE plans SET
    name                      = 'Free Trial',
    price_monthly_usd         = 0.00,
    price_annual_usd          = NULL,
    max_sites                 = 1,
    max_competitors           = 0,
    max_members_default       = 1,
    max_members_hardcap       = 1,
    custom_analyses_per_month = 0,
    timeseries_months         = 0,
    csv_export                = false,
    competitor_comparison     = false,
    competitor_trend_graph    = false,
    default_ai_engines        = 3,
    competitors_per_site      = 0,
    industry_benchmark        = false,
    audit_log_days            = 0,
    data_retention_years      = 5,
    support_tier              = 'self',
    is_enterprise             = false
WHERE id = 'free';

-- basic — $19.99 / 시장 최저가 진입.
UPDATE plans SET
    name                      = 'Basic',
    price_monthly_usd         = 19.99,
    price_annual_usd          = 203.88,   -- $16.99 × 12 (15% 연간 할인)
    max_sites                 = 1,
    max_competitors           = 0,
    max_members_default       = 1,
    max_members_hardcap       = 5,
    custom_analyses_per_month = 5,
    timeseries_months         = 6,
    csv_export                = false,
    competitor_comparison     = false,
    competitor_trend_graph    = false,
    default_ai_engines        = 3,
    competitors_per_site      = 0,
    industry_benchmark        = false,
    audit_log_days            = 0,
    data_retention_years      = 5,
    support_tier              = 'email',
    is_enterprise             = false
WHERE id = 'basic';

-- pro — $79.99 / 시장 빈 구간 ($50~$129) 진입.
UPDATE plans SET
    name                      = 'Pro',
    price_monthly_usd         = 79.99,
    price_annual_usd          = 815.88,   -- $67.99 × 12
    max_sites                 = 3,
    max_competitors           = 0,        -- 경쟁사 한도는 competitors_per_site로 일원화
    max_members_default       = 3,
    max_members_hardcap       = 30,
    custom_analyses_per_month = 30,
    timeseries_months         = 12,
    csv_export                = true,
    competitor_comparison     = true,
    competitor_trend_graph    = false,
    default_ai_engines        = 3,
    competitors_per_site      = 1,
    industry_benchmark        = false,
    audit_log_days            = 30,
    data_retention_years      = 5,
    support_tier              = 'email_chat',
    is_enterprise             = false
WHERE id = 'pro';

-- ─── 4. business / enterprise 신규 INSERT ───
INSERT INTO plans (
    id, name,
    price_monthly_usd, price_annual_usd,
    max_sites, max_competitors,
    max_members_default, max_members_hardcap,
    custom_analyses_per_month, timeseries_months,
    csv_export, competitor_comparison, competitor_trend_graph,
    default_ai_engines, competitors_per_site, industry_benchmark,
    audit_log_days, data_retention_years, support_tier, is_enterprise,
    is_active
) VALUES
    -- business — $299.99 / AthenaHQ Self-Serve 동가, 한국어 차별화.
    (
        'business', 'Business',
        299.99, 3059.88,            -- $254.99 × 12
        5, 0,
        5, 100,
        100, 24,
        true, true, true,
        3, 3, true,
        90, 5, 'email_chat_sla4h', false,
        true
    ),
    -- enterprise — $1,499.99 / Ahrefs Enterprise 동가 + Dedicated CS.
    -- annual commit 필수, wire transfer 허용. -1 = 무제한 표시.
    (
        'enterprise', 'Enterprise',
        1499.99, 15299.88,          -- $1,274.99 × 12 (annual commit 필수)
        -1, -1,
        20, -1,
        -1, -1,
        true, true, true,
        -1, 5, true,
        -1, 7, 'dedicated', true,
        true
    );

COMMIT;
