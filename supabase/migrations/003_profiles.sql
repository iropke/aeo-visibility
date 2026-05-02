-- ============================================================
-- 003_profiles.sql
-- profiles: auth.users(1:1) 확장 — 표시 이름, 언어/타임존, 마케팅 동의 등.
-- SPEC §5-2 profiles 정의를 준수.
-- ============================================================
BEGIN;

CREATE TABLE profiles (
    id                    UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name          TEXT,
    preferred_language    TEXT NOT NULL DEFAULT 'en'
                              CHECK (preferred_language IN ('en', 'ko', 'es')),
    timezone              TEXT NOT NULL DEFAULT 'UTC',
    marketing_consent     BOOLEAN NOT NULL DEFAULT FALSE,
    marketing_consent_at  TIMESTAMPTZ,
    age_verified          BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at         TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── updated_at 자동 갱신 함수 (이후 마이그레이션에서도 재사용) ───
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER profiles_set_updated_at
BEFORE UPDATE ON profiles
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ─── auth.users INSERT 시 profiles 자동 생성 ───
-- Supabase Auth가 생성한 새 유저에 대해 profiles row를 생성.
-- 동일 id로 중복 호출돼도 무시 (예: 마이그레이션 재실행, 백엔드 race).
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO public.profiles (id, display_name)
    VALUES (
        NEW.id,
        NEW.raw_user_meta_data->>'display_name'
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

COMMIT;
