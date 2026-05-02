/**
 * SSR / Route Handler / Server Action 용 Supabase 클라이언트.
 * Next.js 14 cookies()로 세션 유지.
 */
import { createServerClient as createSSRClient } from "@supabase/ssr";
import { cookies } from "next/headers";

import { env } from "@/env";

/**
 * 서버 컴포넌트/라우트 핸들러에서 사용. 호출 시점마다 새 인스턴스 생성.
 *
 * 주의: Server Component에서는 cookies().set이 일부 컨텍스트에서만 가능 →
 * @supabase/ssr가 try/catch로 감싸 처리. middleware/Route Handler/Server Action에서는 정상.
 */
export async function createServerClient() {
  const cookieStore = await cookies();

  return createSSRClient(
    env.NEXT_PUBLIC_SUPABASE_URL,
    env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) => {
              cookieStore.set(name, value, options);
            });
          } catch {
            // Server Component에서 cookies().set 호출 불가한 경우 — 무시.
            // 세션 갱신은 middleware가 처리하므로 일반적으로 문제 없음.
          }
        },
      },
    },
  );
}
