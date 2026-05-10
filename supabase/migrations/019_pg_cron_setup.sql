-- ============================================================
-- 019_pg_cron_setup.sql
-- pg_cron + pg_net 기반 백엔드 cron endpoint 호출.
--
-- 스케줄:
--   monthly-auto-analysis   — 매월 1일 00:00 UTC (자동 분석 트리거, Phase 1 stub)
--   trial-expiry-sequence   — 매일 09:00 UTC    (Day 7/30/90 메일, G8 helper 호출)
--
-- 인증: HMAC-SHA256 (secret 보관: ALTER DATABASE postgres SET app.* = ...).
--   X-Cron-Timestamp = epoch seconds
--   X-Cron-Signature = lower(hex(hmac(timestamp || body, secret, 'sha256')))
--   서버에서 |now - timestamp| ≤ 5분 검사 → replay 차단.
--
-- 사전 설정 (Supabase Studio SQL editor 또는 service_role):
--   ALTER DATABASE postgres SET app.cron_hmac_secret = '<랜덤_64자리>';
--   ALTER DATABASE postgres SET app.api_base_url    = 'https://api.ahxov.com';
--   -- 적용: SELECT pg_reload_conf();  또는 새 connection 부터 반영.
--
-- 등록된 작업 확인:
--   SELECT * FROM cron.job;
--   SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 20;
--
-- 작업 비활성화 / 제거:
--   SELECT cron.unschedule('monthly-auto-analysis');
-- ============================================================
BEGIN;

-- Extensions — Supabase Cloud Pro 티어에서 활성화 가능.
-- 로컬 supabase start 에는 기본 포함됨.
CREATE EXTENSION IF NOT EXISTS pg_cron;
CREATE EXTENSION IF NOT EXISTS pg_net;
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- hmac() 사용

-- internal 스키마 — cron 헬퍼 함수 격리 (사용자 schema 와 분리).
CREATE SCHEMA IF NOT EXISTS internal;

-- ─── HMAC 서명된 백엔드 호출 헬퍼 ─────────────────────────────
-- pg_cron job 본문에서 1줄 호출:
--   SELECT internal.cron_post('/api/internal/cron/monthly-analysis');
--
-- body 인자가 있으면 동일 알고리즘으로 서명 (timestamp || body::text).
CREATE OR REPLACE FUNCTION internal.cron_post(
    path TEXT,
    body JSONB DEFAULT '{}'::jsonb
) RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_secret     TEXT;
    v_base_url   TEXT;
    v_timestamp  TEXT;
    v_signature  TEXT;
    v_body_text  TEXT;
    v_request_id BIGINT;
BEGIN
    v_secret   := current_setting('app.cron_hmac_secret', true);
    v_base_url := current_setting('app.api_base_url',    true);

    IF v_secret IS NULL OR v_secret = '' THEN
        RAISE EXCEPTION 'app.cron_hmac_secret is not set; run ALTER DATABASE postgres SET app.cron_hmac_secret = ...';
    END IF;
    IF v_base_url IS NULL OR v_base_url = '' THEN
        RAISE EXCEPTION 'app.api_base_url is not set; run ALTER DATABASE postgres SET app.api_base_url = ...';
    END IF;

    v_timestamp := extract(epoch FROM now())::bigint::text;
    v_body_text := body::text;
    v_signature := encode(
        hmac(v_timestamp || v_body_text, v_secret, 'sha256'),
        'hex'
    );

    SELECT net.http_post(
        url := v_base_url || path,
        headers := jsonb_build_object(
            'Content-Type',      'application/json',
            'X-Cron-Timestamp',  v_timestamp,
            'X-Cron-Signature',  v_signature
        ),
        body := body
    ) INTO v_request_id;

    RETURN v_request_id;
END;
$$;

COMMENT ON FUNCTION internal.cron_post(TEXT, JSONB) IS
    'HMAC 서명된 백엔드 cron endpoint 호출 — pg_cron job 본문에서 1줄 호출용';


-- ─── 스케줄 ────────────────────────────────────────────────────

-- 매월 1일 00:00 UTC — 자동 분석 트리거 (Phase 1 stub, 본문은 백엔드 라우터).
SELECT cron.schedule(
    'monthly-auto-analysis',
    '0 0 1 * *',
    $cron$ SELECT internal.cron_post('/api/internal/cron/monthly-analysis'); $cron$
);

-- 매일 09:00 UTC — 트라이얼 만료 시퀀스 (Day 7 / 30 / 90, G8 helper 일괄 발송).
SELECT cron.schedule(
    'trial-expiry-sequence',
    '0 9 * * *',
    $cron$ SELECT internal.cron_post('/api/internal/cron/trial-expiry-sequence'); $cron$
);

COMMIT;
