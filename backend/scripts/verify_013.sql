-- ============================================================
-- verify_013.sql
-- partial UNIQUE index uniq_analysis_results_workspace_active 동작 검증.
-- 모두 transaction-rollback — 영구 영향 ❌. 슈퍼유저(postgres) 권한 필요.
-- 실행: psql ... -f backend/scripts/verify_013.sql
-- ============================================================
\echo '=== verify_013.sql start ==='

BEGIN;

DO $$
DECLARE
    v_user_id UUID := gen_random_uuid();
    v_ws_id UUID;
    v_site_id UUID;
    v_a1 UUID;
    v_a2 UUID;
    v_failed BOOLEAN := FALSE;
BEGIN
    -- setup: auth.users → handle_new_user trigger creates profiles automatically.
    INSERT INTO auth.users (
        id, instance_id, email, aud, role, encrypted_password,
        email_confirmed_at, raw_user_meta_data, raw_app_meta_data
    ) VALUES (
        v_user_id, '00000000-0000-0000-0000-000000000000',
        'verify013-' || v_user_id || '@example.com',
        'authenticated', 'authenticated', '',
        NOW(), '{}'::jsonb, '{}'::jsonb
    );

    INSERT INTO workspaces (name, slug, owner_id, plan_id)
    VALUES ('verify013-ws', 'verify013-' || v_user_id, v_user_id, 'free')
    RETURNING id INTO v_ws_id;
    -- triggers auto-add owner member + start trial subscription.

    INSERT INTO sites (workspace_id, url, domain, type)
    VALUES (v_ws_id, 'https://verify013.example.com', 'verify013.example.com', 'own')
    RETURNING id INTO v_site_id;

    -- T1: first queued INSERT succeeds.
    INSERT INTO analysis_results (
        workspace_id, site_id, trigger_type, funding_source,
        triggered_by, categories, analysis_version, status
    ) VALUES (
        v_ws_id, v_site_id, 'manual', 'payg',
        v_user_id, ARRAY['technical'], 'v2.0', 'queued'
    ) RETURNING id INTO v_a1;
    RAISE NOTICE 'T1 PASS: first queued row id=%', v_a1;

    -- T2: second queued INSERT for SAME workspace → unique violation (partial UNIQUE index).
    BEGIN
        INSERT INTO analysis_results (
            workspace_id, site_id, trigger_type, funding_source,
            triggered_by, categories, analysis_version, status
        ) VALUES (
            v_ws_id, v_site_id, 'manual', 'payg',
            v_user_id, ARRAY['content'], 'v2.0', 'queued'
        );
        v_failed := TRUE;
        RAISE NOTICE 'T2 FAIL: expected unique_violation';
    EXCEPTION
        WHEN unique_violation THEN
            RAISE NOTICE 'T2 PASS: 2nd queued row blocked by uniq_analysis_results_workspace_active';
    END;
    IF v_failed THEN RAISE EXCEPTION 'T2 FAIL'; END IF;

    -- T3: 'running' INSERT for same workspace also blocked (queued|running shared scope).
    BEGIN
        INSERT INTO analysis_results (
            workspace_id, site_id, trigger_type, funding_source,
            triggered_by, categories, analysis_version, status
        ) VALUES (
            v_ws_id, v_site_id, 'manual', 'payg',
            v_user_id, ARRAY['authority'], 'v2.0', 'running'
        );
        v_failed := TRUE;
        RAISE NOTICE 'T3 FAIL: expected unique_violation';
    EXCEPTION
        WHEN unique_violation THEN
            RAISE NOTICE 'T3 PASS: running row also blocked (shared queued|running scope)';
    END;
    IF v_failed THEN RAISE EXCEPTION 'T3 FAIL'; END IF;

    -- T4: complete the first analysis → status='completed' frees the partial UNIQUE.
    UPDATE analysis_results SET status='completed', completed_at=NOW() WHERE id = v_a1;

    INSERT INTO analysis_results (
        workspace_id, site_id, trigger_type, funding_source,
        triggered_by, categories, analysis_version, status
    ) VALUES (
        v_ws_id, v_site_id, 'manual', 'payg',
        v_user_id, ARRAY['structured'], 'v2.0', 'queued'
    ) RETURNING id INTO v_a2;
    RAISE NOTICE 'T4 PASS: 2nd queued row allowed after first completed; id=%', v_a2;

    -- T5: 'failed' status also frees the partial UNIQUE.
    UPDATE analysis_results SET status='failed', completed_at=NOW() WHERE id = v_a2;
    INSERT INTO analysis_results (
        workspace_id, site_id, trigger_type, funding_source,
        triggered_by, categories, analysis_version, status
    ) VALUES (
        v_ws_id, v_site_id, 'manual', 'payg',
        v_user_id, ARRAY['visibility'], 'v2.0', 'queued'
    );
    RAISE NOTICE 'T5 PASS: queued allowed after previous failed';

    -- T6: completed/failed rows do NOT block each other (multiple completed allowed).
    INSERT INTO analysis_results (
        workspace_id, site_id, trigger_type, funding_source,
        triggered_by, categories, analysis_version, status
    ) VALUES (
        v_ws_id, v_site_id, 'manual', 'payg',
        v_user_id, ARRAY['technical'], 'v2.0', 'completed'
    );
    INSERT INTO analysis_results (
        workspace_id, site_id, trigger_type, funding_source,
        triggered_by, categories, analysis_version, status
    ) VALUES (
        v_ws_id, v_site_id, 'manual', 'payg',
        v_user_id, ARRAY['content'], 'v2.0', 'completed'
    );
    RAISE NOTICE 'T6 PASS: multiple completed rows allowed (outside partial scope)';

    -- T7: different workspace can have its own queued row simultaneously.
    DECLARE
        v_user2_id UUID := gen_random_uuid();
        v_ws2_id UUID;
        v_site2_id UUID;
    BEGIN
        INSERT INTO auth.users (
            id, instance_id, email, aud, role, encrypted_password,
            email_confirmed_at, raw_user_meta_data, raw_app_meta_data
        ) VALUES (
            v_user2_id, '00000000-0000-0000-0000-000000000000',
            'verify013-b-' || v_user2_id || '@example.com',
            'authenticated', 'authenticated', '',
            NOW(), '{}'::jsonb, '{}'::jsonb
        );
        INSERT INTO workspaces (name, slug, owner_id, plan_id)
        VALUES ('verify013-ws2', 'verify013-b-' || v_user2_id, v_user2_id, 'free')
        RETURNING id INTO v_ws2_id;
        INSERT INTO sites (workspace_id, url, domain, type)
        VALUES (v_ws2_id, 'https://other.example.com', 'other.example.com', 'own')
        RETURNING id INTO v_site2_id;
        INSERT INTO analysis_results (
            workspace_id, site_id, trigger_type, funding_source,
            triggered_by, categories, analysis_version, status
        ) VALUES (
            v_ws2_id, v_site2_id, 'manual', 'payg',
            v_user2_id, ARRAY['technical'], 'v2.0', 'queued'
        );
        RAISE NOTICE 'T7 PASS: different workspace can have its own queued row';
    END;
END $$;

ROLLBACK;
\echo '=== verify_013.sql end (all rolled back) ==='
