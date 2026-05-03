/**
 * 현재 활성 워크스페이스 훅.
 *
 * Phase 1 단순화: localStorage 에 active workspace_id 저장. 사용자 로그인 시
 * 워크스페이스 목록을 받아오면 첫 항목으로 폴백. 다중 워크스페이스 스위처는
 * settings/members 청크에서 도입 예정.
 *
 * 메일 딥링크(/sites/[site_id]/results/[result_id])는 workspace_id 없이 진입 →
 * 호출자가 `resolveSiteWorkspace(siteId)` 로 모든 워크스페이스 순회 lookup.
 */
"use client";

import { useEffect, useState } from "react";

import { workspaceApi, type Workspace } from "@/lib/api/workspaces";

const STORAGE_KEY = "aeo:active_workspace_id";

function readStored(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStored(id: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (id === null) window.localStorage.removeItem(STORAGE_KEY);
    else window.localStorage.setItem(STORAGE_KEY, id);
  } catch {
    /* quota 초과 등 — 무시 */
  }
}

export interface ActiveWorkspaceState {
  workspaces: Workspace[] | null;
  workspace: Workspace | null;
  error: string | null;
  loading: boolean;
  setActive: (id: string) => void;
  refresh: () => void;
}

/** 워크스페이스 목록 + 현재 활성 워크스페이스 결정 + setter. */
export function useActiveWorkspace(): ActiveWorkspaceState {
  const [workspaces, setWorkspaces] = useState<Workspace[] | null>(null);
  const [activeId, setActiveId] = useState<string | null>(() => readStored());
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    workspaceApi
      .list()
      .then((rows) => {
        if (cancelled) return;
        setWorkspaces(rows);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Unknown error");
      });
    return () => {
      cancelled = true;
    };
  }, [tick]);

  // localStorage id 가 현재 목록에 없으면 폴백.
  let workspace: Workspace | null = null;
  if (workspaces && workspaces.length > 0) {
    if (activeId) {
      workspace = workspaces.find((w) => w.id === activeId) ?? null;
    }
    if (workspace === null) {
      workspace = workspaces[0];
    }
  }

  const setActive = (id: string) => {
    setActiveId(id);
    writeStored(id);
  };

  const refresh = () => setTick((t) => t + 1);

  return {
    workspaces,
    workspace,
    error,
    loading: workspaces === null && error === null,
    setActive,
    refresh,
  };
}

/**
 * 메일 딥링크용 — site_id 만 가지고 있을 때 어느 워크스페이스 소속인지 해소.
 *
 * Phase 1: 워크스페이스 1~3 개 가정. 모든 워크스페이스에 대해 GET 시도하다가
 * 200 응답을 받은 첫 워크스페이스 반환. 404 는 다음 워크스페이스로 진행, 그 외
 * 에러는 throw.
 */
export async function resolveSiteWorkspace(
  siteId: string,
): Promise<{ workspace: Workspace; siteWorkspaceId: string } | null> {
  const { sitesApi } = await import("@/lib/api/sites");
  const workspaces = await workspaceApi.list();
  for (const ws of workspaces) {
    try {
      const site = await sitesApi.get(ws.id, siteId);
      return { workspace: ws, siteWorkspaceId: site.workspace_id };
    } catch (err) {
      const status = (err as { status?: number }).status;
      if (status === 404) continue;
      throw err;
    }
  }
  return null;
}
