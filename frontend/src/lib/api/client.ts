/**
 * 백엔드 API fetch 래퍼.
 * 클라이언트에서 호출 시 Supabase 세션의 access_token을 자동으로 첨부.
 */
"use client";

import { env } from "@/env";
import { createClient } from "@/lib/supabase/client";

export interface ApiError extends Error {
  status: number;
  payload: unknown;
}

class ApiErrorImpl extends Error implements ApiError {
  status: number;
  payload: unknown;
  constructor(status: number, payload: unknown, message: string) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

async function getAccessToken(): Promise<string | null> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const token = await getAccessToken();
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${env.NEXT_PUBLIC_BACKEND_URL}${path}`, {
    ...init,
    headers,
  });

  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  const payload = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const message =
      (payload &&
        typeof payload === "object" &&
        "detail" in payload &&
        String((payload as { detail: unknown }).detail)) ||
      `Request failed: ${res.status}`;
    throw new ApiErrorImpl(res.status, payload, message);
  }

  return payload as T;
}
