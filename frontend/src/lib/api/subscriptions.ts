/**
 * Subscription API 호출 — 트라이얼 카운트다운 / 만료 모달 / Pricing 진입.
 * 백엔드 schema: `backend/app/schemas/subscription.py`.
 */
"use client";

import { apiFetch } from "./client";

export type SubscriptionStatus =
  | "trial"
  | "active"
  | "past_due"
  | "canceled"
  | "paused";

export interface Subscription {
  id: string;
  workspace_id: string;
  plan_id: string;
  status: SubscriptionStatus;
  billing_cycle: "monthly" | "annual";
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  canceled_at: string | null;
  trial_ends_at: string | null;
  created_at: string;
  updated_at: string;
}

export const subscriptionApi = {
  get: (workspaceId: string) =>
    apiFetch<Subscription>(`/api/workspaces/${workspaceId}/subscription`),
};
