/**
 * Workspace API 호출 (FastAPI 백엔드).
 * 백엔드 schemas와 매칭 — `backend/app/schemas/workspace.py`.
 */
"use client";

import { apiFetch } from "./client";

export type WorkspaceRole = "owner" | "admin" | "member" | "viewer";

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  primary_language: "en" | "ko" | "es";
  timezone: string;
  owner_id: string;
  plan_id: string;
  created_at: string;
  updated_at: string;
  role: WorkspaceRole | null;
}

export interface WorkspaceMember {
  id: string;
  workspace_id: string;
  user_id: string;
  role: WorkspaceRole;
  invited_by: string | null;
  joined_at: string;
  display_name: string | null;
}

export interface WorkspaceCreatePayload {
  name: string;
  primary_language?: "en" | "ko" | "es";
  timezone?: string;
}

export interface WorkspaceUpdatePayload {
  name?: string;
  primary_language?: "en" | "ko" | "es";
  timezone?: string;
}

export const workspaceApi = {
  list: () => apiFetch<Workspace[]>("/api/workspaces"),

  create: (payload: WorkspaceCreatePayload) =>
    apiFetch<Workspace>("/api/workspaces", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  get: (id: string) => apiFetch<Workspace>(`/api/workspaces/${id}`),

  update: (id: string, payload: WorkspaceUpdatePayload) =>
    apiFetch<Workspace>(`/api/workspaces/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  remove: (id: string) =>
    apiFetch<void>(`/api/workspaces/${id}`, { method: "DELETE" }),

  listMembers: (id: string) =>
    apiFetch<WorkspaceMember[]>(`/api/workspaces/${id}/members`),

  updateMemberRole: (workspaceId: string, userId: string, role: WorkspaceRole) =>
    apiFetch<WorkspaceMember>(
      `/api/workspaces/${workspaceId}/members/${userId}`,
      { method: "PATCH", body: JSON.stringify({ role }) },
    ),

  removeMember: (workspaceId: string, userId: string) =>
    apiFetch<void>(`/api/workspaces/${workspaceId}/members/${userId}`, {
      method: "DELETE",
    }),
};
