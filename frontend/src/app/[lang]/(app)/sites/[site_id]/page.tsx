import { setRequestLocale } from "next-intl/server";

import { isLocale } from "@/lib/i18n/config";
import { SiteDetailView } from "@/components/sites/SiteDetailView";

export default async function SiteDetailPage({
  params,
}: {
  params: Promise<{ lang: string; site_id: string }>;
}) {
  const { lang, site_id } = await params;
  if (!isLocale(lang)) return null;
  setRequestLocale(lang);

  return <SiteDetailView lang={lang} siteId={site_id} />;
}
