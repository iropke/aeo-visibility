import { setRequestLocale } from "next-intl/server";

import { isLocale } from "@/lib/i18n/config";
import { SitesView } from "@/components/sites/SitesView";

export default async function SitesPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  if (!isLocale(lang)) return null;
  setRequestLocale(lang);

  return <SitesView lang={lang} />;
}
