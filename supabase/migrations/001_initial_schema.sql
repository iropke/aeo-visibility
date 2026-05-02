-- ============================================================
-- AEO Visibility - Supabase 초기 스키마
-- Supabase 대시보드 → SQL Editor에서 실행하세요
-- ============================================================

-- UUID 확장 활성화 (Supabase는 기본 활성화)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── 분석 결과 테이블 ───
CREATE TABLE IF NOT EXISTS analysis_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url             TEXT NOT NULL,
    domain          TEXT NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',

    -- 점수
    overall_score       INTEGER,
    grade               VARCHAR(2),
    technical_score     INTEGER,
    technical_details   JSONB,
    structured_score    INTEGER,
    structured_details  JSONB,
    content_score       INTEGER,
    content_details     JSONB,
    authority_score     INTEGER,
    authority_details   JSONB,
    visibility_score    INTEGER,
    visibility_details  JSONB,

    -- 결과
    summary             TEXT,
    recommendations     JSONB,
    error_message       TEXT,
    language            VARCHAR(5) DEFAULT 'en',

    -- 타임스탬프
    created_at      TIMESTAMPTZ DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_analysis_domain ON analysis_results (domain);

-- ─── 리드 테이블 ───
CREATE TABLE IF NOT EXISTS leads (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id     UUID NOT NULL REFERENCES analysis_results(id),
    email           TEXT NOT NULL,
    report_sent     BOOLEAN DEFAULT false,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_leads_email ON leads (email);

-- ─── Row Level Security (RLS) 설정 ───
-- API에서 service_role_key로 접근하므로 RLS는 비활성화
-- 필요시 아래 주석 해제하여 활성화
-- ALTER TABLE analysis_results ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
