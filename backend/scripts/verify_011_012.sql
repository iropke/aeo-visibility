-- Transaction-rollback 함수형 검증: 011_analysis_results + 012_monthly_usage.
-- psql -f 로 실행. 모든 ASSERT가 통과해야 OK. ROLLBACK으로 원상 복구.
\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_ws_id        UUID;
    v_site_id      UUID;
    v_profile_id   UUID;
    v_ar_id        UUID;
    v_mu_id        UUID;
    v_mu_updated_1 TIMESTAMPTZ;
    v_mu_updated_2 TIMESTAMPTZ;
    v_err_caught   BOOLEAN;
    v_count        INT;
    v_b INT; v_bp INT; v_pp INT; v_pg INT;
BEGIN
    -- profiles는 auth.users FK 의존이라 직접 INSERT 불가.
    -- auth.users를 임시로 생성 → handle_new_user 트리거가 profiles 자동 생성.
    -- 전체 트랜잭션이 ROLLBACK되므로 영구 영향 ❌.
    v_profile_id := gen_random_uuid();
    INSERT INTO auth.users (
        id, instance_id, email, aud, role,
        encrypted_password, email_confirmed_at, created_at, updated_at,
        raw_user_meta_data, raw_app_meta_data
    ) VALUES (
        v_profile_id,
        '00000000-0000-0000-0000-000000000000',
        'verify-g1-' || substring(v_profile_id::text, 1, 8) || '@example.com',
        'authenticated', 'authenticated',
        '', NOW(), NOW(), NOW(),
        '{"display_name":"verify-g1"}'::jsonb, '{}'::jsonb
    );
    IF NOT EXISTS (SELECT 1 FROM profiles p WHERE p.id = v_profile_id) THEN
        RAISE EXCEPTION '[SETUP FAIL] handle_new_user trigger did not create profile';
    END IF;

    v_ws_id := gen_random_uuid();
    INSERT INTO workspaces (id, name, slug, primary_language, timezone, owner_id, plan_id)
    VALUES (
        v_ws_id, '__verify_g1__',
        '__verify-g1-' || substring(v_ws_id::text, 1, 8),
        'en', 'UTC', v_profile_id, 'free'
    );

    INSERT INTO sites (workspace_id, url, domain, type)
    VALUES (v_ws_id, 'https://verify-g1.example.com', 'verify-g1.example.com', 'own')
    RETURNING id INTO v_site_id;

    -- ============================================================
    -- analysis_results 테스트
    -- ============================================================

    -- T1: valid manual + base INSERT.
    INSERT INTO analysis_results (
        workspace_id, site_id, trigger_type, funding_source, triggered_by,
        categories, analysis_version, status
    ) VALUES (
        v_ws_id, v_site_id, 'manual', 'base', v_profile_id,
        ARRAY['technical', 'content']::TEXT[], 'v2.0', 'queued'
    ) RETURNING id INTO v_ar_id;
    RAISE NOTICE '[T1 OK] manual+base INSERT';

    -- T2: valid auto + auto INSERT.
    INSERT INTO analysis_results (
        workspace_id, site_id, trigger_type, funding_source,
        categories, analysis_version
    ) VALUES (
        v_ws_id, v_site_id, 'auto', 'auto',
        ARRAY['technical','structured','content','authority','visibility']::TEXT[], 'v2.0'
    );
    RAISE NOTICE '[T2 OK] auto+auto INSERT (5 categories)';

    -- T3: invalid trigger=auto + funding=base → CHECK 위반.
    v_err_caught := FALSE;
    BEGIN
        INSERT INTO analysis_results (
            workspace_id, site_id, trigger_type, funding_source,
            categories, analysis_version
        ) VALUES (
            v_ws_id, v_site_id, 'auto', 'base',
            ARRAY['technical']::TEXT[], 'v2.0'
        );
    EXCEPTION WHEN check_violation THEN
        v_err_caught := TRUE;
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION '[T3 FAIL] auto+base should have failed CHECK'; END IF;
    RAISE NOTICE '[T3 OK] auto+base blocked (CHECK)';

    -- T4: invalid trigger=manual + funding=auto → CHECK 위반.
    v_err_caught := FALSE;
    BEGIN
        INSERT INTO analysis_results (
            workspace_id, site_id, trigger_type, funding_source,
            categories, analysis_version
        ) VALUES (
            v_ws_id, v_site_id, 'manual', 'auto',
            ARRAY['technical']::TEXT[], 'v2.0'
        );
    EXCEPTION WHEN check_violation THEN
        v_err_caught := TRUE;
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION '[T4 FAIL] manual+auto should have failed CHECK'; END IF;
    RAISE NOTICE '[T4 OK] manual+auto blocked (CHECK)';

    -- T5: empty categories array → CHECK 위반.
    v_err_caught := FALSE;
    BEGIN
        INSERT INTO analysis_results (
            workspace_id, site_id, trigger_type, funding_source,
            categories, analysis_version
        ) VALUES (
            v_ws_id, v_site_id, 'manual', 'base',
            ARRAY[]::TEXT[], 'v2.0'
        );
    EXCEPTION WHEN check_violation THEN
        v_err_caught := TRUE;
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION '[T5 FAIL] empty categories should have failed CHECK'; END IF;
    RAISE NOTICE '[T5 OK] empty categories blocked (CHECK)';

    -- T6: overall_score 범위 위반.
    v_err_caught := FALSE;
    BEGIN
        INSERT INTO analysis_results (
            workspace_id, site_id, trigger_type, funding_source,
            categories, analysis_version, overall_score
        ) VALUES (
            v_ws_id, v_site_id, 'manual', 'pro_pack',
            ARRAY['content']::TEXT[], 'v2.0', 150.0
        );
    EXCEPTION WHEN check_violation THEN
        v_err_caught := TRUE;
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION '[T6 FAIL] overall_score=150 should have failed CHECK'; END IF;
    RAISE NOTICE '[T6 OK] overall_score>100 blocked (CHECK)';

    -- T7: duration_ms 음수 차단.
    v_err_caught := FALSE;
    BEGIN
        INSERT INTO analysis_results (
            workspace_id, site_id, trigger_type, funding_source,
            categories, analysis_version, duration_ms
        ) VALUES (
            v_ws_id, v_site_id, 'manual', 'payg',
            ARRAY['content']::TEXT[], 'v2.0', -1
        );
    EXCEPTION WHEN check_violation THEN
        v_err_caught := TRUE;
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION '[T7 FAIL] duration_ms=-1 should have failed CHECK'; END IF;
    RAISE NOTICE '[T7 OK] duration_ms<0 blocked (CHECK)';

    -- T8: ON DELETE CASCADE — site 삭제 시 analysis_results도 사라짐.
    SELECT count(*) INTO v_count FROM analysis_results WHERE site_id = v_site_id;
    IF v_count < 1 THEN RAISE EXCEPTION '[T8 SETUP FAIL] expected >=1 analysis row before DELETE'; END IF;

    DELETE FROM sites WHERE id = v_site_id;  -- hard delete (not soft).
    SELECT count(*) INTO v_count FROM analysis_results WHERE site_id = v_site_id;
    IF v_count <> 0 THEN RAISE EXCEPTION '[T8 FAIL] expected 0 analysis rows after CASCADE, got %', v_count; END IF;
    RAISE NOTICE '[T8 OK] sites CASCADE → analysis_results';

    -- 사이트 재생성 (이후 monthly_usage 테스트는 사이트 불필요하지만 일관성 차원).
    INSERT INTO sites (workspace_id, url, domain, type)
    VALUES (v_ws_id, 'https://verify-g1b.example.com', 'verify-g1b.example.com', 'own')
    RETURNING id INTO v_site_id;

    -- ============================================================
    -- monthly_usage 테스트
    -- ============================================================

    -- M1: valid INSERT.
    INSERT INTO monthly_usage (workspace_id, year_month)
    VALUES (v_ws_id, '2026-05')
    RETURNING id, updated_at INTO v_mu_id, v_mu_updated_1;
    RAISE NOTICE '[M1 OK] monthly_usage INSERT (2026-05)';

    -- M2: UNIQUE violation (workspace_id, year_month).
    v_err_caught := FALSE;
    BEGIN
        INSERT INTO monthly_usage (workspace_id, year_month) VALUES (v_ws_id, '2026-05');
    EXCEPTION WHEN unique_violation THEN
        v_err_caught := TRUE;
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION '[M2 FAIL] duplicate (ws,2026-05) should have failed UNIQUE'; END IF;
    RAISE NOTICE '[M2 OK] UNIQUE (workspace_id, year_month) enforced';

    -- M3: invalid year_month format.
    v_err_caught := FALSE;
    BEGIN
        INSERT INTO monthly_usage (workspace_id, year_month) VALUES (v_ws_id, '2026-13');
    EXCEPTION WHEN check_violation THEN
        v_err_caught := TRUE;
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION '[M3 FAIL] 2026-13 should have failed format CHECK'; END IF;
    RAISE NOTICE '[M3 OK] year_month format CHECK enforced';

    v_err_caught := FALSE;
    BEGIN
        INSERT INTO monthly_usage (workspace_id, year_month) VALUES (v_ws_id, '2026-5');
    EXCEPTION WHEN check_violation THEN
        v_err_caught := TRUE;
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION '[M3b FAIL] 2026-5 should have failed format CHECK'; END IF;
    RAISE NOTICE '[M3b OK] year_month single-digit month rejected';

    -- M4: negative counter.
    v_err_caught := FALSE;
    BEGIN
        UPDATE monthly_usage SET base_analyses_used = -1 WHERE id = v_mu_id;
    EXCEPTION WHEN check_violation THEN
        v_err_caught := TRUE;
    END;
    IF NOT v_err_caught THEN RAISE EXCEPTION '[M4 FAIL] base_used=-1 should have failed CHECK'; END IF;
    RAISE NOTICE '[M4 OK] base_analyses_used<0 blocked (CHECK)';

    -- M5: set_updated_at 트리거 등록 검증.
    -- (단일 트랜잭션 내에서 NOW()가 동일 값을 반환하는 Postgres semantic 때문에
    --  functional 차이값 검증은 cross-tx 환경 필요. 등록 자체로 충분.)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.triggers
        WHERE event_object_table = 'monthly_usage'
          AND trigger_name = 'monthly_usage_set_updated_at'
    ) THEN
        RAISE EXCEPTION '[M5 FAIL] set_updated_at trigger not registered on monthly_usage';
    END IF;
    RAISE NOTICE '[M5 OK] set_updated_at trigger registered';

    -- M6: 카운터 정상 증가.
    UPDATE monthly_usage
    SET base_analyses_used       = base_analyses_used + 1,
        basic_pack_analyses_used = basic_pack_analyses_used + 2,
        pro_pack_analyses_used   = pro_pack_analyses_used + 3,
        payg_analyses_used       = payg_analyses_used + 4
    WHERE id = v_mu_id;
    SELECT base_analyses_used, basic_pack_analyses_used,
           pro_pack_analyses_used, payg_analyses_used
    INTO v_b, v_bp, v_pp, v_pg FROM monthly_usage WHERE id = v_mu_id;
    -- M4는 EXCEPTION으로 rollback되므로 base 값은 INSERT 직후 0 그대로 → +1 = 1.
    IF (v_b, v_bp, v_pp, v_pg) <> (1, 2, 3, 4) THEN
        RAISE EXCEPTION '[M6 FAIL] counter increments wrong: base=% bp=% pp=% pg=%', v_b, v_bp, v_pp, v_pg;
    END IF;
    RAISE NOTICE '[M6 OK] counter increments (base 0→1, bp 0→2, pp 0→3, pg 0→4)';

    -- M7: workspaces ON DELETE CASCADE → monthly_usage row 사라짐.
    DELETE FROM workspaces WHERE id = v_ws_id;
    SELECT count(*) INTO v_count FROM monthly_usage WHERE workspace_id = v_ws_id;
    IF v_count <> 0 THEN RAISE EXCEPTION '[M7 FAIL] expected 0 monthly_usage rows after workspace CASCADE, got %', v_count; END IF;
    RAISE NOTICE '[M7 OK] workspaces CASCADE → monthly_usage';

    RAISE NOTICE '== ALL VERIFY G1 CHECKS PASSED ==';
END;
$$;

ROLLBACK;
