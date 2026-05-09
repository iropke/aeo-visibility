"use client";

import { useTranslations } from "next-intl";

import type { MetricResult } from "./types";

interface Props {
  metric: MetricResult;
}

function formatValue(v: MetricResult["value"]): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "✓" : "✗";
  if (typeof v === "number") {
    return Number.isInteger(v) ? String(v) : v.toFixed(2);
  }
  return String(v);
}

export function MetricRow({ metric }: Props) {
  const t = useTranslations("app.sites.results");
  const weightPct = Math.round(metric.weight * 100);

  return (
    <div
      className={`flex items-start justify-between gap-4 rounded-md border px-3 py-2 ${
        metric.passed
          ? "border-emerald-100 bg-emerald-50/40"
          : "border-amber-100 bg-amber-50/40"
      }`}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-sm">
          <span
            className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-bold ${
              metric.passed
                ? "bg-emerald-500 text-white"
                : "bg-amber-500 text-white"
            }`}
            aria-hidden
          >
            {metric.passed ? "✓" : "!"}
          </span>
          <code className="font-mono text-gs-primary">{metric.key}</code>
          <span
            className={`text-xs font-medium ${
              metric.passed ? "text-emerald-700" : "text-amber-700"
            }`}
          >
            {metric.passed ? t("metric_passed") : t("metric_failed")}
          </span>
        </div>
        {metric.evidence && (
          <p className="mt-1 text-xs text-gs-secondary-1 break-words">
            <span className="font-medium text-gs-secondary-1">
              {t("evidence")}:
            </span>{" "}
            {metric.evidence}
          </p>
        )}
      </div>
      <div className="shrink-0 text-right text-xs text-gs-secondary-1 tabular-nums">
        <div className="text-gs-primary">{formatValue(metric.value)}</div>
        <div>{t("metric_weight", { pct: weightPct })}</div>
        {typeof metric.threshold === "number" && (
          <div>
            {t("metric_threshold", { value: metric.threshold })}
          </div>
        )}
      </div>
    </div>
  );
}
