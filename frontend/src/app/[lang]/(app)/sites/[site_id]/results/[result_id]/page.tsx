import { setRequestLocale } from "next-intl/server";

import { isLocale } from "@/lib/i18n/config";
import { AnalysisResultView } from "@/components/analysis/v2/AnalysisResultView";

export default async function AnalysisResultPage({
  params,
}: {
  params: Promise<{ lang: string; site_id: string; result_id: string }>;
}) {
  const { lang, site_id, result_id } = await params;
  if (!isLocale(lang)) return null;
  setRequestLocale(lang);

  return (
    <AnalysisResultView lang={lang} siteId={site_id} resultId={result_id} />
  );
}
