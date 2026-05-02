/**
 * 환경변수 검증 (zod).
 *
 * Public 변수만 클라이언트 번들에 포함된다 (NEXT_PUBLIC_ prefix).
 * Server-only 변수는 SSR/Route Handler에서만 import 가능.
 */
import { z } from "zod";

const publicSchema = z.object({
  NEXT_PUBLIC_SUPABASE_URL: z.string().url(),
  NEXT_PUBLIC_SUPABASE_ANON_KEY: z.string().min(1),
  NEXT_PUBLIC_BACKEND_URL: z.string().url(),
  NEXT_PUBLIC_SITE_URL: z.string().url().default("http://localhost:3000"),
});

const serverSchema = z.object({
  // 클라이언트 노출 절대 ❌
  SUPABASE_SERVICE_ROLE_KEY: z.string().optional(),
});

const rawPublic = {
  NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
  NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  NEXT_PUBLIC_BACKEND_URL: process.env.NEXT_PUBLIC_BACKEND_URL,
  NEXT_PUBLIC_SITE_URL: process.env.NEXT_PUBLIC_SITE_URL,
};

export const env = publicSchema.parse(rawPublic);

/**
 * Server-only env. import 시점에 evaluate되므로 server에서만 호출.
 * 클라이언트 코드에서 import하면 빌드 시점에 service_role_key가 빈 객체로 잘리지만,
 * 안전을 위해 명시적 호출 권장.
 */
export function getServerEnv() {
  return serverSchema.parse({
    SUPABASE_SERVICE_ROLE_KEY: process.env.SUPABASE_SERVICE_ROLE_KEY,
  });
}
