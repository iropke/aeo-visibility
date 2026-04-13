import { getDictionary } from "@/lib/i18n/getDictionary";
import type { Locale } from "@/lib/i18n/config";
import ResultView from "@/components/analysis/ResultView";

export default async function ResultPage({
  params,
}: {
  params: Promise<{ lang: string; id: string }>;
}) {
  const { lang, id } = await params;
  const dict = await getDictionary(lang as Locale);

  return <ResultView id={id} lang={lang as Locale} dict={dict} />;
}
