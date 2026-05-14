"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { MetricRow } from "./MetricRow";
import type { CategoryMetrics, CategoryName } from "./types";

interface Props {
  category: CategoryName;
  /** raw_metrics[category] — undefined 면 카드 자체를 호출자가 안 그려야 함. */
  data: CategoryMetrics;
}

const TONE: Record<CategoryName, string> = {
  technical: "from-blue-500 to-blue-700",
  structured: "from-violet-500 to-violet-700",
  content: "from-amber-500 to-amber-700",
  authority: "from-rose-500 to-rose-700",
  visibility: "from-emerald-500 to-emerald-700",
};

export function CategoryCard({ category, data }: Props) {
  const t = useTranslations("app.sites");
  const tR = useTranslations("app.sites.results");
  const [open, setOpen] = useState(false);

  const passedCount = data.metrics.filter((m) => m.passed).length;
  const totalCount = data.metrics.length;
  const score = Math.round(data.score);

  return (
    <article className="rounded-2xl border border-gs-quarterly-1 bg-white overflow-hidden">
      <div
        className={`bg-gradient-to-r ${TONE[category]} px-5 py-4 text-white`}
      >
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="text-base font-semibold">
            {t(`categories.${category}`)}
          </h3>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-bold tabular-nums">{score}</span>
            <span className="text-sm opacity-80">/100</span>
          </div>
        </div>
        <div className="mt-2 h-1.5 rounded-full bg-white/20 overflow-hidden">
          <div
            className="h-full bg-white"
            style={{ width: `${Math.max(0, Math.min(100, score))}%` }}
          />
        </div>
        <p className="mt-2 text-xs opacity-80 tabular-nums">
          {passedCount} / {totalCount}
        </p>
      </div>

      <div className="px-5 py-3">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="text-xs font-medium text-gs-secondary-1 hover:text-primary"
        >
          {open ? tR("hide_metrics") : tR("show_metrics")} ({totalCount})
        </button>
        {open && (
          <div className="mt-3 space-y-2">
            {data.metrics.map((m) => (
              <MetricRow key={m.key} metric={m} />
            ))}
          </div>
        )}
      </div>
    </article>
  );
}
