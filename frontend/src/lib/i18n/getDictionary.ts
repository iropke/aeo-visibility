import type { Locale } from "./config";

// v1 (legacy MVP) 사전. v2 페이지는 next-intl 메시지 번들 사용.
// es는 v1에 사전 없음 → en으로 폴백.
const dictionaries: Record<Locale, () => Promise<unknown>> = {
  en: () => import("./dictionaries/en.json").then((m) => m.default),
  ko: () => import("./dictionaries/ko.json").then((m) => m.default),
  es: () => import("./dictionaries/en.json").then((m) => m.default),
};

export async function getDictionary(locale: Locale) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return (dictionaries[locale] ?? dictionaries.en)() as Promise<any>;
}
