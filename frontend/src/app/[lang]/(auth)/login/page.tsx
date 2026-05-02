import Link from "next/link";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { isLocale } from "@/lib/i18n/config";
import { MagicLinkForm } from "@/components/auth/MagicLinkForm";

export default async function LoginPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  if (!isLocale(lang)) return null;
  setRequestLocale(lang);

  const t = await getTranslations("auth.login");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-2">{t("title")}</h1>
        <p className="text-sm text-gray-600">{t("subtitle")}</p>
      </div>
      <MagicLinkForm lang={lang} mode="login" />
      <p className="text-sm text-gray-600 text-center">
        {t("no_account")}{" "}
        <Link href={`/${lang}/signup`} className="text-primary hover:underline">
          {t("signup_link")}
        </Link>
      </p>
    </div>
  );
}
