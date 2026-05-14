-- ============================================================
-- 021_cron_post_search_path_fix.sql
-- internal.cron_post 의 search_path 에 `extensions` 추가.
--
-- 배경: Supabase 는 pgcrypto 를 기본으로 `extensions` 스키마에 설치.
-- 019 / 020 의 cron_post 는 search_path = pg_catalog, public, internal 이라
-- `hmac()` / `encode()` (pgcrypto) lookup 실패 → UndefinedFunctionError.
-- pg_net 은 `public.net` 으로 등록돼 있어 그대로 동작.
-- ============================================================
BEGIN;

CREATE OR REPLACE FUNCTION internal.cron_post(
    path TEXT,
    body JSONB DEFAULT '{}'::jsonb
) RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, internal, extensions
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
        extensions.hmac(v_timestamp || v_body_text, v_secret, 'sha256'),
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

COMMIT;
