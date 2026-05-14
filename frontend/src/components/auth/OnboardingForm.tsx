"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { workspaceApi } from "@/lib/api/workspaces";
import type { Locale } from "@/lib/i18n/config";
import { LanguageSelect } from "@/components/ui/LanguageSelect";

export function OnboardingForm({ lang }: { lang: Locale }) {
  const t = useTranslations("auth.onboarding");
  const router = useRouter();

  const [name, setName] = useState("");
  const [primaryLanguage, setPrimaryLanguage] = useState<Locale>(lang);
  const [timezone, setTimezone] = useState("UTC");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await workspaceApi.create({
        name: name.trim(),
        primary_language: primaryLanguage,
        timezone,
      });
      router.push(`/${lang}/dashboard`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label htmlFor="name" className="block text-sm font-medium mb-1">
          {t("name_label")}
        </label>
        <input
          id="name"
          required
          minLength={1}
          maxLength={100}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t("name_placeholder")}
          className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-primary focus:outline-none"
        />
      </div>
      <div>
        <label htmlFor="lang" className="block text-sm font-medium mb-1">
          {t("language_label")}
        </label>
        <LanguageSelect
          id="lang"
          value={primaryLanguage}
          onChange={setPrimaryLanguage}
        />
      </div>
      <div>
        <label htmlFor="tz" className="block text-sm font-medium mb-1">
          {t("timezone_label")}
        </label>
        <input
          id="tz"
          value={timezone}
          onChange={(e) => setTimezone(e.target.value)}
          placeholder="UTC"
          className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-primary focus:outline-none"
        />
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={submitting || !name.trim()}
        className="w-full rounded-md bg-primary text-white font-medium py-2 hover:opacity-90 disabled:opacity-50"
      >
        {submitting ? t("creating") : t("submit")}
      </button>
    </form>
  );
}
