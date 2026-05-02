-- ============================================================
-- 002_drop_mvp_tables.sql
-- v2 reboot: MVP 테이블 제거 후 v2 스키마로 전환.
-- 운영 데이터는 보존하지 않음 (사용자 합의).
-- v2의 analysis_results는 010_analysis_results.sql에서 workspace 스코프로 재정의.
-- ============================================================
BEGIN;

DROP TABLE IF EXISTS leads CASCADE;
DROP TABLE IF EXISTS analysis_results CASCADE;

COMMIT;
