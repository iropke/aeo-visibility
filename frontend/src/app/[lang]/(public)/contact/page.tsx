import { getTranslations, setRequestLocale } from "next-intl/server";
import { Suspense } from "react";

import { isLocale } from "@/lib/i18n/config";
import { ContactForm } from "@/components/contact/ContactForm";

export default async function ContactPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  if (!isLocale(lang)) return null;
  setRequestLocale(lang);

  const t = await getTranslations("app.contact");

  return (
    <div className="space-y-10 pt-8 sm:pt-14 pb-8">
      <header className="text-center max-w-2xl mx-auto">
        <p className="text-primary font-bold text-xs tracking-[0.16em] uppercase mb-3">
          {t("eyebrow")}
        </p>
        <h1 className="font-serif font-bold text-4xl sm:text-5xl leading-[0.94] tracking-tight mb-5">
          {t("title")}
        </h1>
        <p className="text-gs-secondary-1 text-base sm:text-lg leading-relaxed">
          {t("subtitle")}
        </p>
      </header>

      {/* useSearchParams 가 ContactForm 내부에서 호출 — Suspense 필수 (Next.js 14). */}
      <Suspense fallback={<ContactFormSkeleton />}>
        <ContactForm lang={lang} />
      </Suspense>
    </div>
  );
}

function ContactFormSkeleton() {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6 sm:p-8 max-w-xl mx-auto h-[600px] animate-pulse" />
  );
}
