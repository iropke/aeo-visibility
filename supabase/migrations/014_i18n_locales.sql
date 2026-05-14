-- ============================================================
-- 014_i18n_locales.sql
-- i18n 20 lang 확장: profiles.preferred_language + workspaces.primary_language
-- CHECK 제약 ('en','ko','es') → 사용자 지정 20 lang 으로 교체.
--
-- 20 lang 정렬 순서 (셀렉트 박스 노출 순서 = 사용자 지정):
-- en, zh, ja, de, fr, es, ko, pt, hi, ru,
-- nl, it, ar, sv, th, pl, id, ms, da, tr
--
-- 단일 소스 미러:
-- - frontend/src/lib/i18n/config.ts (LOCALES_ORDERED)
-- - backend/app/core/locales.py     (SUPPORTED_LANGS)
--
-- F-i18n-1 청크 (2026-05-09).
-- ============================================================
BEGIN;

-- ─── profiles.preferred_language ───
ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_preferred_language_check;

ALTER TABLE profiles
    ADD CONSTRAINT profiles_preferred_language_check
    CHECK (preferred_language IN (
        'en', 'zh', 'ja', 'de', 'fr', 'es', 'ko', 'pt', 'hi', 'ru',
        'nl', 'it', 'ar', 'sv', 'th', 'pl', 'id', 'ms', 'da', 'tr'
    ));

-- ─── workspaces.primary_language ───
ALTER TABLE workspaces DROP CONSTRAINT IF EXISTS workspaces_primary_language_check;

ALTER TABLE workspaces
    ADD CONSTRAINT workspaces_primary_language_check
    CHECK (primary_language IN (
        'en', 'zh', 'ja', 'de', 'fr', 'es', 'ko', 'pt', 'hi', 'ru',
        'nl', 'it', 'ar', 'sv', 'th', 'pl', 'id', 'ms', 'da', 'tr'
    ));

-- ─── 검증 ───
-- 기존 데이터(en/ko/es)는 새 제약에 모두 포함 → 데이터 마이그레이션 ❌.
-- 추후 lang 추가/제거 시 본 마이그레이션 + frontend/backend 단일 소스 동시 갱신.

COMMIT;
