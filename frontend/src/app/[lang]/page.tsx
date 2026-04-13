import { getDictionary } from "@/lib/i18n/getDictionary";
import type { Locale } from "@/lib/i18n/config";
import UrlForm from "@/components/analysis/UrlForm";

export default async function LandingPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  const dict = await getDictionary(lang as Locale);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] pt-12 sm:pt-20">
      {/* Hero */}
      <div className="text-center max-w-2xl mx-auto mb-10 animate-fade-in-up">
        <p className="text-primary font-bold text-xs tracking-[0.16em] uppercase mb-4">
          {dict.hero_eyebrow}
        </p>
        <h1 className="font-serif font-bold text-4xl sm:text-5xl lg:text-6xl leading-[0.94] tracking-tight mb-6 whitespace-pre-line">
          {dict.hero_title}
        </h1>
        <p className="text-gs-secondary-1 text-base sm:text-lg leading-relaxed max-w-lg mx-auto">
          {dict.hero_description}
        </p>
      </div>

      {/* URL Form */}
      <div className="w-full max-w-xl mx-auto animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
        <UrlForm lang={lang as Locale} dict={dict} />
      </div>
    </div>
  );
}
