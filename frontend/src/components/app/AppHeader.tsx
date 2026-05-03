"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";

import { createClient } from "@/lib/supabase/client";

export function AppHeader({ lang }: { lang: string }) {
  const t = useTranslations("app.nav");
  const router = useRouter();

  async function onLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push(`/${lang}/login`);
  }

  return (
    <header className="sticky top-0 z-50 w-full border-b border-gray-200 bg-white/80 backdrop-blur">
      <nav className="flex items-center justify-between px-5 sm:px-8 min-h-[64px] max-w-shell mx-auto">
        <Link href={`/${lang}/dashboard`} className="flex items-center gap-2">
          <span className="text-lg font-bold tracking-tight">
            AEO <span className="text-primary">Visibility</span>
          </span>
        </Link>
        <div className="flex items-center gap-4 text-sm">
          <Link href={`/${lang}/dashboard`} className="hover:text-primary">
            {t("dashboard")}
          </Link>
          <Link href={`/${lang}/sites`} className="hover:text-primary">
            {t("sites")}
          </Link>
          <Link href={`/${lang}/settings/workspace`} className="hover:text-primary">
            {t("settings")}
          </Link>
          <button onClick={onLogout} className="hover:text-primary">
            {t("logout")}
          </button>
        </div>
      </nav>
    </header>
  );
}
