/**
 * next-intl request 설정.
 * URL 경로의 [lang] 세그먼트에서 locale을 가져와 메시지 번들 로드.
 */
import { getRequestConfig } from "next-intl/server";
import { notFound } from "next/navigation";

import { defaultLocale, isLocale } from "./config";

export default getRequestConfig(async ({ requestLocale }) => {
  const requested = await requestLocale;
  const locale = requested && isLocale(requested) ? requested : defaultLocale;

  let messages;
  try {
    messages = (await import(`@/messages/${locale}.json`)).default;
  } catch {
    notFound();
  }

  return {
    locale,
    messages,
  };
});
