/**
 * Analyses API 호출 — 백엔드 `app.routers.analyses` + `app.schemas.analysis` 와 매칭.
 *
 * 트리거 응답은 202 Accepted + status='queued' — 클라이언트는 list / active 폴링.
 *
 * 백엔드 enforce 규칙:
 *   402 Payment Required  — 트라이얼 만료 또는 quota 부족 (allow_payg=False)
 *   403 Forbidden         — viewer 권한 부족 (action 가드)
 *   404 Not Found         — site/workspace/result 없음
 *   409 Conflict          — 워크스페이스 단위 진행 중 분석 1건 제한
 *   429 Too Many Requests — 1시간 cooldown
 */
"use client";

import { apiFetch } from "./client";

export type AnalysisStatus = "queued" | "running" | "completed" | "failed";

export type AnalysisTriggerType = "manual" | "scheduled" | "monthly_auto";

export type AnalysisFundingSource =
  | "pro_pack"
  | "basic_pack"
  | "base"
  | "payg"
  | "addon"
  | "trial";

export type CategoryName =
  | "technical"
  | "structured"
  | "content"
  | "authority"
  | "visibility";

export const ALL_CATEGORIES: CategoryName[] = [
  "technical",
  "structured",
  "content",
  "authority",
  "visibility",
];

export interface AnalysisResultListItem {
  id: string;
  site_id: string;
  workspace_id: string;
  trigger_type: AnalysisTriggerType;
  funding_source: AnalysisFundingSource;
  status: AnalysisStatus;
  triggered_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  categories: string[];
  /** Decimal — JSON 으로 string 으로 직렬화될 수 있어 union. */
  overall_score: number | string | null;
  analysis_version: string;
}

export interface AnalysisResultDetail extends AnalysisResultListItem {
  triggered_by: string | null;
  category_scores: Record<string, unknown> | null;
  raw_metrics: Record<string, unknown> | null;
  insights: Record<string, unknown> | null;
  improvements: Record<string, unknown> | null;
  error_message: string | null;
}

export interface ActiveAnalysisItem {
  id: string;
  site_id: string;
  status: AnalysisStatus;
  triggered_at: string;
  categories: string[];
}

export interface PackQuota {
  quota: number; // -1 = unlimited
  used: number;
  remaining: number; // -1 = unlimited
}

export interface QuotaResponse {
  year_month: string;
  pro_pack: PackQuota;
  basic_pack: PackQuota;
  base: PackQuota;
  payg_used: number;
}

export interface AnalyzePayload {
  /** None=전체 5축, 1개 이상 지정 시 부분 분석. */
  categories?: CategoryName[] | null;
  /** Phase 1 결제 미연동: 항상 false. */
  allow_payg?: boolean;
}

export const analysesApi = {
  trigger: (
    workspaceId: string,
    siteId: string,
    payload: AnalyzePayload = {},
  ) =>
    apiFetch<AnalysisResultDetail>(
      `/api/workspaces/${workspaceId}/sites/${siteId}/analyze`,
      {
        method: "POST",
        body: JSON.stringify({
          categories: payload.categories ?? null,
          allow_payg: payload.allow_payg ?? false,
        }),
      },
    ),

  list: (
    workspaceId: string,
    siteId: string,
    opts: { limit?: number; offset?: number } = {},
  ) => {
    const params = new URLSearchParams();
    if (opts.limit !== undefined) params.set("limit", String(opts.limit));
    if (opts.offset !== undefined) params.set("offset", String(opts.offset));
    const qs = params.toString();
    return apiFetch<AnalysisResultListItem[]>(
      `/api/workspaces/${workspaceId}/sites/${siteId}/analyses${qs ? `?${qs}` : ""}`,
    );
  },

  get: (workspaceId: string, siteId: string, resultId: string) =>
    apiFetch<AnalysisResultDetail>(
      `/api/workspaces/${workspaceId}/sites/${siteId}/analyses/${resultId}`,
    ),

  active: (workspaceId: string) =>
    apiFetch<ActiveAnalysisItem[]>(
      `/api/workspaces/${workspaceId}/analyses/active`,
    ),

  quota: (workspaceId: string) =>
    apiFetch<QuotaResponse>(`/api/workspaces/${workspaceId}/usage/current`),
};

/** 진행 중(queued|running)인 status 인지. */
export function isActiveStatus(status: AnalysisStatus): boolean {
  return status === "queued" || status === "running";
}
