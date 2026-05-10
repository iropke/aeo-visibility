-- ============================================================
-- 020_internal_app_config.sql
-- internal.cron_post 의 secret/base_url 보관 — `ALTER DATABASE postgres SET app.*`
-- 대체.
--
-- 배경: Supabase pooler 의 postgres role 은 `is_superuser=off` 라 `ALTER DATABASE`
-- / `ALTER ROLE ... SET` 가 InsufficientPrivilege 로 실패. Studio Web UI 의 SQL
-- editor 만 superuser 권한으로 실행 가능 → 매 시크릿 갱신 때마다 Web UI 의존.
--
-- 본 마이그레이션은 같은 `internal` 스키마에 `app_config` 테이블을 두고
-- `internal.cron_post` 가 그 테이블을 SELECT 하도록 함. INSERT/UPDATE 는 pooler 의
-- postgres / service_role 에 GRANT.
--
-- 시크릿 갱신 절차:
--   INSERT INTO internal.app_config (key, value) VALUES ('cron_hmac_secret', '<HEX>')
--     ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();
--   INSERT INTO internal.app_config (key, value) VALUES ('api_base_url', '<URL>')
--     ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW();
-- ============================================================
BEGIN;

-- ─── 테이블 ───
CREATE TABLE IF NOT EXISTS internal.app_config (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE internal.app_config IS
    'cron_post HMAC secret + base URL 등 cluster-level 설정 보관. service_role / postgres 만 R/W.';

-- 권한 — 일반 사용자 차단, postgres + service_role 만 사용.
REVOKE ALL ON internal.app_config FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON internal.app_config TO postgres, service_role;

-- ─── cron_post 교체 — current_setting() 대신 internal.app_config SELECT ───
CREATE OR REPLACE FUNCTION internal.cron_post(
    path TEXT,
    body JSONB DEFAULT '{}'::jsonb
) RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, internal
AS $$
DECLARE
    v_secret     TEXT;
    v_base_url   TEXT;
    v_timestamp  TEXT;
    v_signature  TEXT;
    v_body_text  TEXT;
    v_request_id BIGINT;
BEGIN
    SELECT value INTO v_secret
        FROM internal.app_config WHERE key = 'cron_hmac_secret';
    SELECT value INTO v_base_url
        FROM internal.app_config WHERE key = 'api_base_url';

    IF v_secret IS NULL OR v_secret = '' THEN
        RAISE EXCEPTION
            'internal.app_config[''cron_hmac_secret''] missing — INSERT INTO internal.app_config (key,value) VALUES (''cron_hmac_secret'',''<hex>'') ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value';
    END IF;
    IF v_base_url IS NULL OR v_base_url = '' THEN
        RAISE EXCEPTION
            'internal.app_config[''api_base_url''] missing — INSERT INTO internal.app_config (key,value) VALUES (''api_base_url'',''<url>'') ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value';
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
    'HMAC 서명된 백엔드 cron endpoint 호출 — secret/base_url 은 internal.app_config 에서 lookup';

COMMIT;
