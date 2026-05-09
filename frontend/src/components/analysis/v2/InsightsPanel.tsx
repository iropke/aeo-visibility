"use client";

import { useTranslations } from "next-intl";

import type { InsightsBlob } from "./types";

interface Props {
  insights: InsightsBlob | null;
  lang: string;
}

export function InsightsPanel({ insights, lang }: Props) {
  const t = useTranslations("app.sites.results");

  if (!insights) {
    return (
      <p className="text-sm text-gs-secondary-1">
        {t("insights_unavailable")}
      </p>
    );
  }

  const summary =
    insights.summary?.[lang] ??
    insights.summary?.en ??
    "";

  return (
    <div className="rounded-2xl border border-gs-quarterly-1 bg-white p-5 space-y-3">
      {summary ? (
        <p className="text-sm text-gs-primary leading-relaxed whitespace-pre-line">
          {summary}
        </p>
      ) : (
        <p className="text-sm text-gs-secondary-1">
          {t("insights_unavailable")}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-gs-quarterly-1">
        {insights.synthesized_by && (
          <span className="text-xs text-gs-secondary-2">
            {t("insights_synthesized_by", { model: insights.synthesized_by })}
          </span>
        )}
        {insights.high_priority_capped && (
          <span className="text-xs text-amber-700">
            {t("insights_high_priority_capped")}
          </span>
        )}
      </div>
    </div>
  );
}
