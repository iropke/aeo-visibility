/**
 * (public) 라우트 그룹 레이아웃 — 마케팅/위키/법적 페이지용.
 * v1 Header/Footer를 그대로 사용 (legacy MVP 구조).
 */
import type { Locale } from "@/lib/i18n/config";
import { getDictionary } from "@/lib/i18n/getDictionary";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";

export default async function PublicLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const dict = (await getDictionary(lang as Locale)) as any;

  return (
    <>
      <Header lang={lang as Locale} dict={dict} />
      <main className="flex-1 w-full max-w-shell mx-auto px-4 sm:px-5 pt-8 pb-20">
        {children}
      </main>
      <Footer dict={dict} />
    </>
  );
}
