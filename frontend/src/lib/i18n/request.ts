/**
 * next-intl request 설정.
 * URL 경로의 [lang] 세그먼트에서 locale을 가져와 메시지 번들 로드.
 * en.json 을 fallback base 로 deep-merge → 19 lang 미번역 키는 영어로 표시.
 */
import { getRequestConfig } from "next-intl/server";
import { notFound } from "next/navigation";

import { defaultLocale, isLocale } from "./config";

type JsonValue = string | number | boolean | null | JsonValue[] | { [k: string]: JsonValue };
type Messages = { [k: string]: JsonValue };

function deepMerge(base: Messages, override: Messages): Messages {
  const out: Messages = { ...base };
  for (const key of Object.keys(override)) {
    const b = out[key];
    const o = override[key];
    if (
      b &&
      o &&
      typeof b === "object" &&
      typeof o === "object" &&
      !Array.isArray(b) &&
      !Array.isArray(o)
    ) {
      out[key] = deepMerge(b as Messages, o as Messages);
    } else {
      out[key] = o;
    }
  }
  return out;
}

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;
  const locale = requested && isLocale(requested) ? requested : defaultLocale;

  // en 은 항상 base fallback (영어 키 누락 시 빌드/런타임 실패하면 안 됨).
  let base: Messages;
  try {
    base = (await import(`@/messages/en.json`)).default as Messages;
  } catch {
    notFound();
  }

  if (locale === "en") {
    return { locale, messages: base };
  }

  try {
    const localeMessages = (await import(`@/messages/${locale}.json`))
      .default as Messages;
    return { locale, messages: deepMerge(base, localeMessages) };
  } catch {
    // locale 파일 자체가 없으면 영어로 풀백.
    return { locale, messages: base };
  }
});
