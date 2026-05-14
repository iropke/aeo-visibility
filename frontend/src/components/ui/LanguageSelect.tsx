"use client";

import type { ChangeEvent, SelectHTMLAttributes } from "react";

import { LOCALES_ORDERED, LOCALE_META, type Locale, isLocale } from "@/lib/i18n/config";

type NativeSelectProps = Omit<
  SelectHTMLAttributes<HTMLSelectElement>,
  "value" | "onChange" | "children"
>;

interface LanguageSelectProps extends NativeSelectProps {
  value: Locale;
  onChange: (next: Locale) => void;
  /** "native" (default) → 한국어, "english" → Korean, "both" → 한국어 (Korean) */
  labelMode?: "native" | "english" | "both";
}

const BASE_CLASS =
  "block w-full rounded-md border border-gs-tertiary-2 bg-white text-gs-primary text-sm px-3 py-2 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50";

function formatLabel(locale: Locale, mode: "native" | "english" | "both"): string {
  const meta = LOCALE_META[locale];
  if (mode === "english") return meta.englishName;
  if (mode === "both") return `${meta.nativeName} (${meta.englishName})`;
  return meta.nativeName;
}

export function LanguageSelect({
  value,
  onChange,
  labelMode = "native",
  className = "",
  ...rest
}: LanguageSelectProps) {
  const handleChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const next = event.target.value;
    if (isLocale(next)) onChange(next);
  };

  return (
    <select
      {...rest}
      value={value}
      onChange={handleChange}
      className={`${BASE_CLASS} ${className}`}
    >
      {LOCALES_ORDERED.map((code) => (
        <option key={code} value={code}>
          {formatLabel(code, labelMode)}
        </option>
      ))}
    </select>
  );
}
