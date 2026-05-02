/**
 * 브라우저용 Supabase 클라이언트.
 * Anon key 사용 — RLS 적용됨.
 */
"use client";

import { createBrowserClient } from "@supabase/ssr";

import { env } from "@/env";

export function createClient() {
  return createBrowserClient(
    env.NEXT_PUBLIC_SUPABASE_URL,
    env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  );
}
