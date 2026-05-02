import { getTranslations, setRequestLocale } from "next-intl/server";

import { isLocale } from "@/lib/i18n/config";

export default async function VerifyPage({
  params,
  searchParams,
}: {
  params: Promise<{ lang: string }>;
  searchParams: Promise<{ email?: string }>;
}) {
  const { lang } = await params;
  if (!isLocale(lang)) return null;
  setRequestLocale(lang);

  const { email } = await searchParams;
  const t = await getTranslations("auth.verify");

  return (
    <div className="space-y-6 text-center">
      <h1 className="text-2xl font-bold">{t("title")}</h1>
      <p className="text-sm text-gray-700">
        {t("subtitle", { email: email || "" })}
      </p>
      <p className="text-xs text-gray-500">{t("did_not_receive")}</p>
    </div>
  );
}
