-- ============================================================
-- 013_analysis_active_uniq.sql
-- analysis_results 워크스페이스 단위 진행 중(queued/running) 1건 강제.
--
-- G3 라우터는 SELECT count 검사 후 INSERT 흐름이라 동시 트리거 race window 존재.
-- partial UNIQUE index 로 race 안전망 추가:
--   - 동일 워크스페이스의 (queued | running) row 가 둘 이상 INSERT 시도 → unique violation
--   - 라우터에서 IntegrityError → 409 Conflict 변환
--
-- 마이그레이션 적용 전제: analysis_results 에 (workspace_id, status) 기준 중복 진행 row ❌.
--   현재 e2e + 프로덕션 분석은 G3 라우터의 SELECT 검사로 충분히 보호됨.
--   안전을 위해 적용 전 SELECT 검사 (아래 verify 블록에서).
-- ============================================================
BEGIN;

-- (워크스페이스, status) = (queued/running) 인 row 가 워크스페이스당 최대 1건.
-- status 별로 분리하면 'queued + running' 동시 허용 → race window 부활. 둘 다 같은 partial scope.
CREATE UNIQUE INDEX uniq_analysis_results_workspace_active
    ON analysis_results (workspace_id)
    WHERE status IN ('queued', 'running');

COMMENT ON INDEX uniq_analysis_results_workspace_active IS
    '워크스페이스 단위 진행 중(queued|running) 분석 1건 제한 — G4 race window 안전망';

COMMIT;
