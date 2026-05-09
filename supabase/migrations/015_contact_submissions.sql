-- ============================================================
-- 015_contact_submissions.sql
-- 2026-05-09 F3-pricing 청크.
--
-- 공개 Contact 폼 (`/{lang}/contact`) 응답을 저장. 인증 없이 누구나 INSERT 가능 +
-- 백엔드 service_role 만 SELECT/UPDATE (운영자 처리 상태 변경).
--
-- 처리 상태(`contact_status` ENUM): new → in_progress → resolved 또는 spam.
-- Phase 1 admin UI ❌ (별도 admin 패널 청크). 운영자는 supabase 콘솔 SQL 또는
-- 추후 admin endpoint 로 status 변경. 본 마이그레이션은 데이터 모델 + RLS 만.
--
-- 어뷰징 방지: 라우터 단 honeypot 필드 + IP rate limit (`services/rate_limit.py`).
-- ip_hash 는 sha256 (평문 IP 미저장 — 개인정보 최소).
--
-- 관련 docs: SPEC §4-5 어뷰징 방지 / DEV_SPEC §7-2 마이그레이션 번호.
-- ============================================================
BEGIN;

-- ─── ENUM ───
CREATE TYPE contact_status AS ENUM ('new', 'in_progress', 'resolved', 'spam');
CREATE TYPE contact_topic  AS ENUM ('demo', 'sales', 'support', 'general');

-- ─── 테이블 ───
CREATE TABLE contact_submissions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    email           TEXT NOT NULL,
    company         TEXT,
    topic           contact_topic NOT NULL DEFAULT 'general',
    message         TEXT NOT NULL,
    locale          TEXT NOT NULL DEFAULT 'en',  -- 요청 시점 lang (i18n 폴백 참고용)
    referrer_url    TEXT,
    ip_hash         TEXT,                        -- sha256(salt + ip) — 어뷰저 추적용
    user_agent      TEXT,
    status          contact_status NOT NULL DEFAULT 'new',
    resolved_by     UUID REFERENCES profiles(id) ON DELETE SET NULL,
    resolved_at     TIMESTAMPTZ,
    notes           TEXT,                         -- 운영자 메모
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT contact_submissions_email_chk CHECK (email LIKE '%@%'),
    CONSTRAINT contact_submissions_message_len_chk CHECK (char_length(message) BETWEEN 1 AND 5000),
    CONSTRAINT contact_submissions_name_len_chk CHECK (char_length(name) BETWEEN 1 AND 200)
);

CREATE INDEX idx_contact_submissions_status_created
    ON contact_submissions(status, created_at DESC);

CREATE INDEX idx_contact_submissions_email
    ON contact_submissions(email);

-- 어뷰저 추적용 (동일 IP 의 최근 응답).
CREATE INDEX idx_contact_submissions_ip_recent
    ON contact_submissions(ip_hash, created_at DESC)
    WHERE ip_hash IS NOT NULL;

CREATE TRIGGER contact_submissions_set_updated_at
BEFORE UPDATE ON contact_submissions
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ============================================================
-- RLS — service_role only (백엔드 단독 접근).
-- 인증된 사용자/anon 둘 다 직접 접근 ❌. POST 폼은 백엔드 라우터를 거침.
-- 향후 admin 패널 청크에서 platform_admin role + 정책 확장.
-- ============================================================
ALTER TABLE contact_submissions ENABLE ROW LEVEL SECURITY;

-- 명시적 정책 ❌ → authenticated/anon 모두 차단.
-- service_role 은 RLS 자체를 우회하므로 별도 정책 불필요.

COMMIT;
