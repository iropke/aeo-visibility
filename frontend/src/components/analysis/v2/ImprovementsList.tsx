"use client";

import { useTranslations } from "next-intl";

import type { Improvement, ImprovementsBlob } from "./types";
import { pickDescription } from "./types";

interface Props {
  improvements: ImprovementsBlob | null;
  lang: string;
}

const PRIORITY_TONE: Record<Improvement["priority"], string> = {
  high: "bg-rose-100 text-rose-800 ring-rose-200",
  medium: "bg-amber-100 text-amber-800 ring-amber-200",
  low: "bg-slate-100 text-slate-700 ring-slate-200",
};

const EFFORT_TONE: Record<Improvement["estimated_effort"], string> = {
  low: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  medium: "bg-amber-50 text-amber-700 ring-amber-200",
  high: "bg-rose-50 text-rose-700 ring-rose-200",
};

export function ImprovementsList({ improvements, lang }: Props) {
  const t = useTranslations("app.sites.results");
  const tCat = useTranslations("app.sites.categories");

  const items: Improvement[] = improvements?.items ?? [];

  if (items.length === 0) {
    return (
      <p className="text-sm text-gs-secondary-1">{t("improvements_empty")}</p>
    );
  }

  return (
    <ol className="space-y-3">
      {items.map((it, idx) => {
        const desc = pickDescription(it.description, lang);
        return (
          <li
            key={`${it.title_key}-${idx}`}
            className="rounded-2xl border border-gs-quarterly-1 bg-white p-5"
          >
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <span
                className={`inline-flex items-center rounded-pill px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${PRIORITY_TONE[it.priority]}`}
              >
                {t(`improvement_priority.${it.priority}`)}
              </span>
              <span className="text-xs font-medium text-gs-secondary-1">
                {tCat(it.category)}
              </span>
              <span
                className={`ml-auto inline-flex items-center rounded-pill px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${EFFORT_TONE[it.estimated_effort]}`}
              >
                {t(`improvement_effort.${it.estimated_effort}`)}
              </span>
              <span className="text-xs text-gs-secondary-1 tabular-nums">
                {t("improvement_impact", { value: it.estimated_impact })}
              </span>
            </div>
            <p className="text-sm font-medium text-gs-primary mb-1">
              <code className="font-mono text-xs text-gs-secondary-1">
                {it.title_key}
              </code>
            </p>
            {desc && (
              <p className="text-sm text-gs-primary leading-relaxed whitespace-pre-line">
                {desc}
              </p>
            )}
            {it.related_metric_keys.length > 0 && (
              <p className="mt-2 text-xs text-gs-secondary-1">
                <span className="font-medium">
                  {t("improvement_related_metrics")}:
                </span>{" "}
                {it.related_metric_keys.map((k) => (
                  <code key={k} className="font-mono mr-2">
                    {k}
                  </code>
                ))}
              </p>
            )}
          </li>
        );
      })}
    </ol>
  );
}
