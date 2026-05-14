import Link from "next/link";
import type { Dictionary } from "@/types/analysis";

export default function Footer({ dict, lang }: { dict: Dictionary; lang: string }) {
  const linkClass =
    "hover:text-gs-primary transition-colors";

  return (
    <footer className="relative z-10 mt-auto py-6 px-5 border-t border-gs-quarterly-1">
      <div className="max-w-shell mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <p className="text-xs tracking-wider uppercase text-gs-secondary-2">
          &copy; {new Date().getFullYear()} {dict.footer_powered}
        </p>
        <nav
          aria-label="Legal"
          className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs tracking-wider uppercase text-gs-secondary-2"
        >
          <Link href={`/${lang}/pricing`} className={linkClass}>
            Pricing
          </Link>
          <Link href={`/${lang}/contact`} className={linkClass}>
            Contact
          </Link>
          <Link href={`/${lang}/legal/terms`} className={linkClass}>
            Terms
          </Link>
          <Link href={`/${lang}/legal/privacy`} className={linkClass}>
            Privacy
          </Link>
          <Link href={`/${lang}/legal/refund`} className={linkClass}>
            Refund
          </Link>
        </nav>
      </div>
    </footer>
  );
}
