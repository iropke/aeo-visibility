-- ============================================================
-- 009_subscriptions.sql
-- subscriptions: 워크스페이스의 결제/트라이얼 상태 머신.
--
-- SPEC §5-2 subscriptions 정합. workspace 1:N subscriptions이지만 정상 운영 시
-- 워크스페이스당 active(또는 trial) 1건이 일반적. 해지 후 재구독 시 history
-- 보존을 위해 UNIQUE 제약은 두지 않음.
--
-- 트라이얼 자동 시작:
--   workspace 생성 직후 status='trial' + plan_id='free' + trial_ends_at=NOW()+7일
--   row가 SECURITY DEFINER 트리거로 자동 INSERT.
--   trial 한도값은 plans('free') row의 컬럼값으로 enforce — 별도 분기 ❌.
--
-- Stripe 통합(Phase 2)은 service_role로 webhook이 직접 UPDATE/INSERT.
-- 일반 사용자는 SELECT만 가능 (자기 워크스페이스의 구독 상태 조회).
-- ============================================================
BEGIN;

CREATE TYPE subscription_status AS ENUM
    ('trial', 'active', 'past_due', 'canceled', 'paused');

CREATE TABLE subscriptions (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id             UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    stripe_subscription_id   TEXT UNIQUE,                              -- Phase 2에서 attach
    plan_id                  TEXT NOT NULL REFERENCES plans(id),
    status                   subscription_status NOT NULL DEFAULT 'trial',
    billing_cycle            TEXT NOT NULL DEFAULT 'monthly'
                                 CHECK (billing_cycle IN ('monthly', 'annual')),
    current_period_start     TIMESTAMPTZ,
    current_period_end       TIMESTAMPTZ,
    cancel_at_period_end     BOOLEAN NOT NULL DEFAULT FALSE,
    canceled_at              TIMESTAMPTZ,
    trial_ends_at            TIMESTAMPTZ,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_workspace ON subscriptions(workspace_id);
CREATE INDEX idx_subscriptions_status    ON subscriptions(status);
-- 트라이얼 만료 cron (Phase 2)에서 사용할 partial index.
CREATE INDEX idx_subscriptions_trial_ends_at
    ON subscriptions(trial_ends_at)
    WHERE status = 'trial' AND trial_ends_at IS NOT NULL;

CREATE TRIGGER subscriptions_set_updated_at
BEFORE UPDATE ON subscriptions
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- ─── 워크스페이스 생성 시 7-day trial 자동 시작 ───
-- AFTER INSERT 트리거. SECURITY DEFINER로 RLS 우회 (워크스페이스 생성자가
-- 직접 subscriptions에 INSERT 하지 않으므로 INSERT 정책 불요).
CREATE OR REPLACE FUNCTION public.start_trial_for_new_workspace()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO public.subscriptions (
        workspace_id, plan_id, status, billing_cycle, trial_ends_at
    ) VALUES (
        NEW.id, 'free', 'trial', 'monthly', NOW() + INTERVAL '7 days'
    );
    RETURN NEW;
END;
$$;

CREATE TRIGGER workspaces_start_trial
AFTER INSERT ON workspaces
FOR EACH ROW EXECUTE FUNCTION public.start_trial_for_new_workspace();

-- ============================================================
-- RLS: 멤버는 자기 워크스페이스의 구독 SELECT만 가능.
-- INSERT는 트리거(SECURITY DEFINER)만, UPDATE/DELETE는 service_role만 (Phase 2 webhook).
-- ============================================================
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY subscriptions_select ON subscriptions FOR SELECT
    TO authenticated
    USING (workspace_id IN (SELECT public.user_workspace_ids(auth.uid())));

-- INSERT/UPDATE/DELETE 정책 부재 = authenticated 일반 사용자 차단.
-- Stripe webhook(Phase 2)은 service_role 키로 RLS 우회.

COMMIT;
