/**
 * i18n 단일 소스 — 20 lang 사용자 지정 정렬 순서.
 * - LOCALES_ORDERED: 셀렉트 박스 노출 순서 (alphabetical ❌, 사용자 지정).
 * - locales: type derivation + generateStaticParams.
 * - LOCALE_META: native name / English name / RTL 플래그.
 *
 * 추가/변경 시 함께 갱신:
 * - backend/app/core/locales.py (단일 소스 미러)
 * - supabase/migrations/014_i18n_locales.sql 의 CHECK 제약
 * - frontend/messages/{lang}.json (translate_i18n.py 로 자동 생성)
 */

export const LOCALES_ORDERED = [
  "en",
  "zh",
  "ja",
  "de",
  "fr",
  "es",
  "ko",
  "pt",
  "hi",
  "ru",
  "nl",
  "it",
  "ar",
  "sv",
  "th",
  "pl",
  "id",
  "ms",
  "da",
  "tr",
] as const;

export type Locale = (typeof LOCALES_ORDERED)[number];

// next-intl / generateStaticParams 호환을 위한 alias.
export const locales = LOCALES_ORDERED;

export const defaultLocale: Locale = "en";

export const RTL_LOCALES: ReadonlySet<Locale> = new Set(["ar"]);

export interface LocaleMeta {
  /** ISO 639-1 code */
  code: Locale;
  /** Native autonym (셀렉트 박스 표시용) */
  nativeName: string;
  /** English exonym (디버그/관리 화면용) */
  englishName: string;
  /** Right-to-left script flag */
  rtl: boolean;
}

export const LOCALE_META: Record<Locale, LocaleMeta> = {
  en: { code: "en", nativeName: "English", englishName: "English", rtl: false },
  zh: { code: "zh", nativeName: "中文", englishName: "Mandarin", rtl: false },
  ja: { code: "ja", nativeName: "日本語", englishName: "Japanese", rtl: false },
  de: { code: "de", nativeName: "Deutsch", englishName: "German", rtl: false },
  fr: { code: "fr", nativeName: "Français", englishName: "French", rtl: false },
  es: { code: "es", nativeName: "Español", englishName: "Spanish", rtl: false },
  ko: { code: "ko", nativeName: "한국어", englishName: "Korean", rtl: false },
  pt: { code: "pt", nativeName: "Português", englishName: "Portuguese", rtl: false },
  hi: { code: "hi", nativeName: "हिन्दी", englishName: "Hindi", rtl: false },
  ru: { code: "ru", nativeName: "Русский", englishName: "Russian", rtl: false },
  nl: { code: "nl", nativeName: "Nederlands", englishName: "Dutch", rtl: false },
  it: { code: "it", nativeName: "Italiano", englishName: "Italian", rtl: false },
  ar: { code: "ar", nativeName: "العربية", englishName: "Arabic", rtl: true },
  sv: { code: "sv", nativeName: "Svenska", englishName: "Swedish", rtl: false },
  th: { code: "th", nativeName: "ไทย", englishName: "Thai", rtl: false },
  pl: { code: "pl", nativeName: "Polski", englishName: "Polish", rtl: false },
  id: { code: "id", nativeName: "Bahasa Indonesia", englishName: "Indonesian", rtl: false },
  ms: { code: "ms", nativeName: "Bahasa Melayu", englishName: "Malay", rtl: false },
  da: { code: "da", nativeName: "Dansk", englishName: "Danish", rtl: false },
  tr: { code: "tr", nativeName: "Türkçe", englishName: "Turkish", rtl: false },
};

export function isLocale(value: string): value is Locale {
  return (LOCALES_ORDERED as readonly string[]).includes(value);
}

export function isRtl(locale: Locale): boolean {
  return RTL_LOCALES.has(locale);
}

export function getDirection(locale: Locale): "rtl" | "ltr" {
  return isRtl(locale) ? "rtl" : "ltr";
}
