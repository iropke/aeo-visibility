/**
 * Service role 클라이언트 — RLS 우회.
 *
 * ⚠️ 절대 클라이언트 컴포넌트나 브라우저 코드에서 import 금지.
 * 일반적인 백엔드 작업은 별도 FastAPI 백엔드를 호출하지만,
 * Next.js Route Handler에서 Storage 등 Supabase 직접 작업이 필요할 때만 사용.
 */
import "server-only";

import { createClient } from "@supabase/supabase-js";

import { env } from "@/env";

export function createAdminClient() {
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!serviceRoleKey) {
    throw new Error(
      "SUPABASE_SERVICE_ROLE_KEY is not set. Required for admin client.",
    );
  }
  return createClient(env.NEXT_PUBLIC_SUPABASE_URL, serviceRoleKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}
