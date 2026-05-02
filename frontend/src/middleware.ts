/**
 * Combined middleware:
 *   1. Locale prefix가 없으면 Accept-Language 기반 redirect.
 *   2. Supabase 세션 쿠키 갱신 (모든 요청).
 *   3. 보호된 경로는 미인증 시 /[lang]/login으로 redirect.
 *   4. 이미 인증된 사용자가 (auth) 페이지에 접근 시 /[lang]/dashboard로 redirect.
 *
 * 통과 경로 (matcher 외):
 *   - /auth/callback   (Supabase Magic Link callback, locale 없음)
 *   - /_next/*, /api/*, 정적 파일
 */
import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

import { defaultLocale, isLocale } from "@/lib/i18n/config";

// 인증이 필요한 경로 (locale prefix 다음 부분).
const PROTECTED_PREFIXES = [
  "/dashboard",
  "/sites",
  "/reports",
  "/qa",
  "/settings",
  "/onboarding",
];

// 인증된 사용자가 접근 시 dashboard로 보낼 경로.
const AUTH_ONLY_PREFIXES = ["/login", "/signup", "/verify"];

function detectLocale(request: NextRequest): string {
  const accept = request.headers.get("accept-language") || "";
  for (const candidate of accept
    .toLowerCase()
    .split(",")
    .map((s) => s.split(";")[0].trim())) {
    const short = candidate.slice(0, 2);
    if (isLocale(short)) return short;
  }
  return defaultLocale;
}

function pathWithoutLocale(pathname: string): { locale: string | null; rest: string } {
  const segments = pathname.split("/");
  // segments[0] = '', segments[1] = locale 후보.
  if (segments.length >= 2 && isLocale(segments[1])) {
    return { locale: segments[1], rest: "/" + segments.slice(2).join("/") };
  }
  return { locale: null, rest: pathname };
}

function matchesAny(rest: string, prefixes: string[]): boolean {
  return prefixes.some((p) => rest === p || rest.startsWith(p + "/"));
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 1. Pass-through.
  if (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.startsWith("/auth/callback") ||
    pathname.includes(".")
  ) {
    return NextResponse.next();
  }

  // 2. Locale 감지/redirect.
  const { locale: pathLocale, rest } = pathWithoutLocale(pathname);
  if (!pathLocale) {
    const target = detectLocale(request);
    const url = request.nextUrl.clone();
    url.pathname = `/${target}${pathname === "/" ? "" : pathname}`;
    if (url.pathname === "") url.pathname = `/${target}`;
    return NextResponse.redirect(url);
  }

  // 3. Supabase 세션 동기화.
  let response = NextResponse.next({ request });
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options),
          );
        },
      },
    },
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();

  // 4. 인증 가드.
  const isProtected = matchesAny(rest, PROTECTED_PREFIXES);
  const isAuthOnly = matchesAny(rest, AUTH_ONLY_PREFIXES);

  if (isProtected && !user) {
    const url = request.nextUrl.clone();
    url.pathname = `/${pathLocale}/login`;
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  if (isAuthOnly && user) {
    const url = request.nextUrl.clone();
    url.pathname = `/${pathLocale}/dashboard`;
    return NextResponse.redirect(url);
  }

  return response;
}

export const config = {
  matcher: ["/((?!_next|favicon.ico).*)"],
};
