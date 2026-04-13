import Link from "next/link";
import type { Locale } from "@/lib/i18n/config";
import type { Dictionary } from "@/types/analysis";

export default function Header({ lang, dict }: { lang: Locale; dict: Dictionary }) {
  const otherLang = lang === "en" ? "ko" : "en";
  const otherLabel = lang === "en" ? "KO" : "EN";

  return (
    <header className="sticky top-0 z-50 w-full">
      <nav className="glass-card !rounded-none flex items-center justify-between px-5 sm:px-8 min-h-[72px]">
        <Link href={`/${lang}`} className="flex items-center gap-2">
          <span className="text-lg font-bold tracking-tight text-gs-primary">
            AEO <span className="text-primary">Visibility</span>
          </span>
        </Link>

        <div className="flex items-center gap-3">
          <Link
            href={`/${otherLang}`}
            className="inline-flex items-center justify-center min-w-[40px] h-[40px] px-3 rounded-pill border border-transparent text-xs font-bold uppercase tracking-wider text-gs-secondary-2 hover:text-gs-primary hover:border-primary/20 hover:bg-primary/5 transition-all"
          >
            {otherLabel}
          </Link>
        </div>
      </nav>
    </header>
  );
}
