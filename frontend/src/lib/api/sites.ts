/**
 * Sites API 호출 — 백엔드 `app.routers.sites` + `app.schemas.site` 와 매칭.
 *
 * 백엔드 enforce 규칙 (라우터에서 발생 가능한 status):
 *   400 Bad Request          — URL 파싱 실패 (도메인 없음)
 *   403 Forbidden            — plan max_sites / competitors_per_site 한도 초과
 *   404 Not Found            — site/workspace 없음
 *   409 Conflict             — 동일 도메인 활성 또는 30일 cooldown
 *   429 Too Many Requests    — URL 교체 1회/월 한도
 *   402 Payment Required     — 트라이얼 만료 게이팅 (write 엔드포인트)
 */
"use client";

import { apiFetch } from "./client";

export type SiteType = "own" | "competitor";

export interface Site {
  id: string;
  workspace_id: string;
  url: string;
  domain: string;
  nickname: string | null;
  type: SiteType;
  last_analyzed_at: string | null;
  last_url_changed_at: string | null;
  deleted_at: string | null;
  delete_cooldown_until: string | null;
  created_at: string;
  updated_at: string;
}

export interface SiteCreatePayload {
  url: string;
  nickname?: string | null;
  type?: SiteType;
}

export interface SiteUpdatePayload {
  url?: string;
  nickname?: string | null;
}

export const sitesApi = {
  list: (workspaceId: string, includeDeleted = false) => {
    const qs = includeDeleted ? "?include_deleted=true" : "";
    return apiFetch<Site[]>(`/api/workspaces/${workspaceId}/sites${qs}`);
  },

  get: (workspaceId: string, siteId: string) =>
    apiFetch<Site>(`/api/workspaces/${workspaceId}/sites/${siteId}`),

  create: (workspaceId: string, payload: SiteCreatePayload) =>
    apiFetch<Site>(`/api/workspaces/${workspaceId}/sites`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  update: (workspaceId: string, siteId: string, payload: SiteUpdatePayload) =>
    apiFetch<Site>(`/api/workspaces/${workspaceId}/sites/${siteId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  remove: (workspaceId: string, siteId: string) =>
    apiFetch<void>(`/api/workspaces/${workspaceId}/sites/${siteId}`, {
      method: "DELETE",
    }),
};
