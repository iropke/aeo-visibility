-- ============================================================
-- 004_plans.sql
-- plans: 마스터 시드 (free/basic/medium/pro/premium).
-- SPEC §5-2 plans + DEV_SPEC §7-4 seed 정의 준수.
-- 가격, custom 한도, 멤버 한도는 잠정 — 시장조사 세션 결과 반영 시 UPDATE.
-- ============================================================
BEGIN;

CREATE TABLE plans (
    id                          TEXT PRIMARY KEY,
    name                        TEXT NOT NULL,
    price_monthly_usd           NUMERIC(10,2) NOT NULL,
    price_annual_usd            NUMERIC(10,2),
    max_sites                   INT NOT NULL,
    max_competitors             INT NOT NULL DEFAULT 0,
    max_members_default         INT NOT NULL DEFAULT 1,
    max_members_hardcap         INT NOT NULL DEFAULT 1,
    custom_analyses_per_month   INT NOT NULL DEFAULT 0,
    timeseries_months           INT NOT NULL DEFAULT 0,  -- 0 = 무제한
    csv_export                  BOOLEAN NOT NULL DEFAULT FALSE,
    competitor_comparison       BOOLEAN NOT NULL DEFAULT FALSE,
    competitor_trend_graph      BOOLEAN NOT NULL DEFAULT FALSE,
    stripe_price_id_monthly     TEXT,
    stripe_price_id_annual      TEXT,
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE
);

-- ─── 시드 데이터 ───
-- 연간 가격: monthly * 12 * 0.85 (15% 할인, 잠정)
INSERT INTO plans (
    id, name,
    price_monthly_usd, price_annual_usd,
    max_sites, max_competitors,
    max_members_default, max_members_hardcap,
    custom_analyses_per_month, timeseries_months,
    csv_export, competitor_comparison, competitor_trend_graph,
    is_active
) VALUES
    ('free',    'Free Trial', 0.00,   NULL,    1, 0, 1, 1,   0,  0, false, false, false, true),
    ('basic',   'Basic',      7.99,   81.49,   1, 0, 1, 1,   3,  3, false, false, false, true),
    ('medium',  'Medium',     23.99,  244.69,  3, 0, 3, 30,  10, 12, false, false, false, true),
    ('pro',     'Pro',        59.99,  611.89,  1, 1, 3, 30,  20, 24, true,  true,  false, true),
    ('premium', 'Premium',    99.99,  1019.89, 1, 3, 5, 50,  30, 0,  true,  true,  true,  true);

COMMIT;
