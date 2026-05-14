import { getTranslations, setRequestLocale } from "next-intl/server";

import { isLocale } from "@/lib/i18n/config";
import { listPlansSafe } from "@/lib/api/plans";
import { PricingCards } from "@/components/pricing/PricingCards";

// 빌드 시점 backend unreachable 보호 + 가격 변경 즉시 반영 (Phase 2 쿠폰).
export const revalidate = 3600;
export const dynamic = "force-dynamic";

export default async function PricingPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  if (!isLocale(lang)) return null;
  setRequestLocale(lang);

  const t = await getTranslations("app.pricing");

  // 빌드 시점 backend unreachable → 빈 배열 폴백. 런타임 fetch 시 실제 데이터로 갱신.
  // Phase 2 쿠폰 청크 진입 시 본 호출 결과 자체가 적용된 가격이 됨.
  const plans = await listPlansSafe({ revalidate: 3600 });

  return (
    <div className="space-y-12 pt-8 sm:pt-14 pb-8">
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

      <PricingCards plans={plans} lang={lang} />

      <div className="text-center text-sm text-gs-secondary-1 max-w-xl mx-auto">
        {t("footnote")}
      </div>
    </div>
  );
}
