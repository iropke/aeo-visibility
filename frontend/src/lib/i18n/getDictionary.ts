import type { Locale } from "./config";

// v1 (legacy MVP) 사전. v2 페이지는 next-intl 메시지 번들 (`@/messages`) 사용.
// v1 dictionaries 는 마케팅 페이지(`(public)/result/[id]`)만 활용 → en 만 보유, 그 외 lang 은 en 폴백.
const v1Dictionaries: Partial<Record<Locale, () => Promise<unknown>>> = {
  en: () => import("./dictionaries/en.json").then((m) => m.default),
  ko: () => import("./dictionaries/ko.json").then((m) => m.default),
};

export async function getDictionary(locale: Locale) {
  const loader = v1Dictionaries[locale] ?? v1Dictionaries.en!;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return loader() as Promise<any>;
}
