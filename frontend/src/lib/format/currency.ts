/**
 * 가격 포맷터 — Intl.NumberFormat 기반 lang 별 통화 표시.
 *
 * Phase 1: 모든 플랜 가격은 USD. lang 별 통화 기호/소수 자릿수만 분기.
 * Phase 2 다중 통화 시 ``currency`` 파라미터 인자로 받음 (인터페이스 변경 ❌).
 *
 * `-1` (무제한 표기) 는 별도 처리 — 호출자가 ``isUnlimited`` 체크 후 i18n 라벨 사용.
 */

const SUPPORTED_BCP47: Record<string, string> = {
  en: "en-US",
  zh: "zh-CN",
  ja: "ja-JP",
  de: "de-DE",
  fr: "fr-FR",
  es: "es-ES",
  ko: "ko-KR",
  pt: "pt-BR",
  hi: "hi-IN",
  ru: "ru-RU",
  nl: "nl-NL",
  it: "it-IT",
  ar: "ar-SA",
  sv: "sv-SE",
  th: "th-TH",
  pl: "pl-PL",
  id: "id-ID",
  ms: "ms-MY",
  da: "da-DK",
  tr: "tr-TR",
};

/**
 * USD 가격을 lang 별 형식으로 포맷.
 *
 * ``$19.99`` (en) / ``19,99 $`` (de) / ``USD 19.99`` (zh) 등.
 * 소수점 자릿수는 .99 같은 cents 가 있으면 2자리, 정수면 0자리.
 */
export function formatUSD(amount: number | string, lang: string = "en"): string {
  const num = typeof amount === "string" ? Number(amount) : amount;
  if (!Number.isFinite(num)) return "";
  const locale = SUPPORTED_BCP47[lang] ?? "en-US";
  const fractionDigits = Number.isInteger(num) ? 0 : 2;
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(num);
}

/** 연간 가격을 12개월로 나눈 월 환산 — Intl 로 동일 포맷. */
export function formatUSDPerMonthFromAnnual(
  annualAmount: number | string,
  lang: string = "en",
): string {
  const num = typeof annualAmount === "string" ? Number(annualAmount) : annualAmount;
  if (!Number.isFinite(num)) return "";
  return formatUSD(Math.round((num / 12) * 100) / 100, lang);
}

/** ``-1`` 무제한 표기 헬퍼. */
export function isUnlimited(value: number): boolean {
  return value === -1;
}
