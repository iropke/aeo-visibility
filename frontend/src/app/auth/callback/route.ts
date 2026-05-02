/**
 * Supabase Magic Link callback.
 *
 * 흐름:
 *   1. 사용자가 이메일 링크 클릭 → /auth/callback?code=xxx&next=/en/dashboard
 *   2. Supabase가 code를 세션으로 교환.
 *   3. 성공 시 next 경로로 redirect (워크스페이스 없으면 onboarding으로).
 *   4. 실패 시 /[lang]/login?error=...
 *
 * 이 라우트는 locale prefix 없음 — Supabase의 redirect URL이 고정 path를 사용.
 */
import { NextResponse } from "next/server";

import { defaultLocale, isLocale } from "@/lib/i18n/config";
import { createServerClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const next = searchParams.get("next") ?? `/${defaultLocale}/dashboard`;

  // next 경로에서 lang 추출 (login redirect 시 언어 보존).
  const langFromNext = next.split("/")[1] ?? defaultLocale;
  const lang = isLocale(langFromNext) ? langFromNext : defaultLocale;

  if (!code) {
    return NextResponse.redirect(`${origin}/${lang}/login?error=missing_code`);
  }

  const supabase = await createServerClient();
  const { error } = await supabase.auth.exchangeCodeForSession(code);

  if (error) {
    return NextResponse.redirect(
      `${origin}/${lang}/login?error=${encodeURIComponent(error.message)}`,
    );
  }

  // 사용자가 워크스페이스 멤버십이 있는지 확인 — 없으면 onboarding으로.
  // 단순히 server에서 백엔드 호출은 토큰 전파가 까다로워 — 클라이언트가 dashboard에서 분기 처리.
  return NextResponse.redirect(`${origin}${next}`);
}
