/**
 * (app) 라우트 그룹 레이아웃 — 인증된 사용자 전용 (dashboard, sites, settings ...).
 * 미들웨어가 미인증 사용자를 /[lang]/login으로 리디렉션하므로 여기서는 추가 가드 없음.
 *
 * 사이드바/탑바 등 본격 chrome은 후속 청크에서 추가.
 */
import type { Locale } from "@/lib/i18n/config";
import { AppHeader } from "@/components/app/AppHeader";

export default async function AppLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  return (
    <>
      <AppHeader lang={lang as Locale} />
      <main className="flex-1 w-full max-w-shell mx-auto px-4 sm:px-5 pt-8 pb-20">
        {children}
      </main>
    </>
  );
}
