import { getDictionary } from "@/lib/i18n/getDictionary";
import type { Locale as V2Locale } from "@/lib/i18n/config";
import type { Locale as V1Locale } from "@/types/analysis";
import ResultView from "@/components/analysis/ResultView";

export default async function ResultPage({
  params,
}: {
  params: Promise<{ lang: string; id: string }>;
}) {
  const { lang, id } = await params;
  const dict = await getDictionary(lang as V2Locale);
  // v1 ResultView 는 ("en" | "ko") 만 받음 — "es" 는 dict 폴백과 동일하게 en 처리.
  const v1Lang: V1Locale = lang === "ko" ? "ko" : "en";

  return <ResultView id={id} lang={v1Lang} dict={dict} />;
}
