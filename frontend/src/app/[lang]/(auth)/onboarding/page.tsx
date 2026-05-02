import { getTranslations, setRequestLocale } from "next-intl/server";

import { isLocale } from "@/lib/i18n/config";
import { OnboardingForm } from "@/components/auth/OnboardingForm";

export default async function OnboardingPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  if (!isLocale(lang)) return null;
  setRequestLocale(lang);

  const t = await getTranslations("auth.onboarding");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-2">{t("title")}</h1>
        <p className="text-sm text-gray-600">{t("subtitle")}</p>
      </div>
      <OnboardingForm lang={lang} />
    </div>
  );
}
