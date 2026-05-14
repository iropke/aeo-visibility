/**
 * 트라이얼 상태 / 잔여 일수 / 임박 모달 트리거 결정 훅.
 *
 * AppHeader 의 잔여 일수 배지 + 페이지 진입 시 1회 모달 트리거에 사용.
 *
 * 단계 구분 (배지 색상 / 모달 트리거):
 *   safe    — > 7일      (녹색, 모달 ❌)
 *   warning — 3~7일      (앰버, 모달 ❌)
 *   urgent  — 0~3일      (적색, 1회 모달)
 *   expired — trial_ends_at < NOW() (적색, 1회 모달)
 *
 * 모달 dedupe: localStorage `aeo:trial_modal_dismissed_<ws>_<YYYY-MM-DD>` —
 * 워크스페이스 × 날짜 단위로 1회 dismiss 시 같은 날 재진입에서 모달 ❌.
 */
"use client";

import { useEffect, useMemo, useState } from "react";

import { subscriptionApi, type Subscription } from "@/lib/api/subscriptions";
import { useApi } from "./useApi";

export type TrialStage = "safe" | "warning" | "urgent" | "expired" | "not_trial";

export interface TrialStatus {
  loading: boolean;
  error: string | null;
  subscription: Subscription | null;
  /** 트라이얼 종료까지 남은 일 (반올림 내림). 만료 후 음수, 트라이얼 아니면 null. */
  daysRemaining: number | null;
  stage: TrialStage;
  /** UI 가 카운트다운 배지를 표시해야 하는가. */
  showBadge: boolean;
  /** 임박/만료 모달을 트리거해야 하는가. localStorage dedupe 적용. */
  shouldShowModal: boolean;
  /** 모달 dismiss — 같은 날 재진입 시 모달 차단. */
  dismissModal: () => void;
}

const URGENT_DAYS = 3;
const WARNING_DAYS = 7;
const DISMISS_KEY_PREFIX = "aeo:trial_modal_dismissed:";

function todayUtcKey(): string {
  const d = new Date();
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
}

function dismissKey(workspaceId: string): string {
  return `${DISMISS_KEY_PREFIX}${workspaceId}:${todayUtcKey()}`;
}

function readDismissed(workspaceId: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(dismissKey(workspaceId)) === "1";
  } catch {
    return false;
  }
}

function writeDismissed(workspaceId: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(dismissKey(workspaceId), "1");
  } catch {
    /* quota / private mode — 무시 */
  }
}

function diffDays(future: string): number {
  const ms = new Date(future).getTime() - Date.now();
  return Math.floor(ms / (24 * 60 * 60 * 1000));
}

function classifyStage(sub: Subscription | null): {
  daysRemaining: number | null;
  stage: TrialStage;
} {
  if (!sub || sub.status !== "trial" || !sub.trial_ends_at) {
    return { daysRemaining: null, stage: "not_trial" };
  }
  const days = diffDays(sub.trial_ends_at);
  if (days < 0) return { daysRemaining: days, stage: "expired" };
  if (days <= URGENT_DAYS) return { daysRemaining: days, stage: "urgent" };
  if (days <= WARNING_DAYS) return { daysRemaining: days, stage: "warning" };
  return { daysRemaining: days, stage: "safe" };
}

/**
 * @param workspaceId 활성 워크스페이스 — null/undefined 면 fetch ❌.
 */
export function useTrialStatus(workspaceId: string | null | undefined): TrialStatus {
  const sq = useApi(
    () => subscriptionApi.get(workspaceId!),
    [workspaceId ?? null],
    { enabled: !!workspaceId },
  );

  // dismissed 상태 — 컴포넌트 mount 시 1회 read.
  const [dismissed, setDismissed] = useState<boolean>(false);
  useEffect(() => {
    if (!workspaceId) return;
    setDismissed(readDismissed(workspaceId));
  }, [workspaceId]);

  const { daysRemaining, stage } = useMemo(
    () => classifyStage(sq.data),
    [sq.data],
  );

  const showBadge = stage === "warning" || stage === "urgent" || stage === "expired";
  const shouldShowModal =
    !dismissed && (stage === "urgent" || stage === "expired");

  const dismissModal = () => {
    if (!workspaceId) return;
    writeDismissed(workspaceId);
    setDismissed(true);
  };

  return {
    loading: sq.loading,
    error: sq.error?.message ?? null,
    subscription: sq.data,
    daysRemaining,
    stage,
    showBadge,
    shouldShowModal,
    dismissModal,
  };
}
