"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { RadarChart } from "@/components/charts/RadarChart";
import {
  analysesApi,
  isActiveStatus,
  type AnalysisFundingSource,
  type AnalysisResultDetail,
  type AnalysisStatus,
  type AnalysisTriggerType,
  type CategoryName,
} from "@/lib/api/analyses";
import { sitesApi, type Site } from "@/lib/api/sites";
import {
  resolveSiteWorkspace,
  useActiveWorkspace,
} from "@/lib/hooks/useActiveWorkspace";
import { useApi } from "@/lib/hooks/useApi";

import { CategoryCard } from "./CategoryCard";
import { ImprovementsList } from "./ImprovementsList";
import { InsightsPanel } from "./InsightsPanel";
import {
  toNumber,
  type CategoryMetrics,
  type ImprovementsBlob,
  type InsightsBlob,
  type RawMetrics,
} from "./types";

interface Props {
  lang: string;
  siteId: string;
  resultId: string;
}

const ALL_CATEGORIES: CategoryName[] = [
  "technical",
  "structured",
  "content",
  "authority",
  "visibility",
];

const POLL_MS = 2500;

export function AnalysisResultView({ lang, siteId, resultId }: Props) {
  const t = useTranslations("app.sites.results");
  const tSites = useTranslations("app.sites");
  const tCommon = useTranslations("common");

  const ws = useActiveWorkspace();

  // 1) site lookup — 활성 워크스페이스 먼저, 404 면 전체 워크스페이스 순회 (메일 딥링크).
  const [site, setSite] = useState<Site | null>(null);
  const [siteWorkspaceId, setSiteWorkspaceId] = useState<string | null>(null);
  const [siteError, setSiteError] = useState<string | null>(null);
  const [siteLoading, setSiteLoading] = useState(true);

  useEffect(() => {
    if (!ws.workspace) return;
    let cancelled = false;
    setSiteLoading(true);
    setSiteError(null);

    (async () => {
      try {
        const found = await sitesApi.get(ws.workspace!.id, siteId);
        if (!cancelled) {
          setSite(found);
          setSiteWorkspaceId(ws.workspace!.id);
          setSiteLoading(false);
        }
      } catch (err) {
        const status = (err as { status?: number }).status;
        if (status !== 404) {
          if (!cancelled) {
            setSiteError(err instanceof Error ? err.message : String(err));
            setSiteLoading(false);
          }
          return;
        }
        try {
          const resolved = await resolveSiteWorkspace(siteId);
          if (cancelled) return;
          if (resolved === null) {
            setSiteError("not_found");
            setSiteLoading(false);
            return;
          }
          ws.setActive(resolved.workspace.id);
          const found = await sitesApi.get(resolved.workspace.id, siteId);
          if (cancelled) return;
          setSite(found);
          setSiteWorkspaceId(resolved.workspace.id);
          setSiteLoading(false);
        } catch (err2) {
          if (!cancelled) {
            setSiteError(err2 instanceof Error ? err2.message : String(err2));
            setSiteLoading(false);
          }
        }
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ws.workspace?.id, siteId]);

  // 2) result fetch + status='running' 폴링.
  const resultQ = useApi<AnalysisResultDetail>(
    () => analysesApi.get(siteWorkspaceId!, siteId, resultId),
    [siteWorkspaceId, siteId, resultId],
    { enabled: !!siteWorkspaceId },
  );

  const isRunning =
    resultQ.data !== null && isActiveStatus(resultQ.data.status);

  // status='running' 동안만 추가 폴링.
  const polling = useApi<AnalysisResultDetail>(
    () => analysesApi.get(siteWorkspaceId!, siteId, resultId),
    [siteWorkspaceId, siteId, resultId, isRunning],
    {
      enabled: !!siteWorkspaceId && isRunning,
      pollIntervalMs: isRunning ? POLL_MS : 0,
    },
  );

  // polling 결과로 resultQ.data 갱신.
  useEffect(() => {
    if (polling.data && !isActiveStatus(polling.data.status)) {
      resultQ.refresh();
    }
  }, [polling.data, resultQ]);

  const display = polling.data ?? resultQ.data;

  // ── render ─────────────────────────────────────────────
  if (ws.loading || (siteLoading && site === null)) {
    return <p className="text-sm text-gs-secondary-1">{tCommon("loading")}</p>;
  }
  if (ws.error) {
    return (
      <p className="text-sm text-red-600">
        {tCommon("error")}: {ws.error}
      </p>
    );
  }
  if (siteError === "not_found" || (site === null && !siteLoading)) {
    return (
      <div className="rounded-md border border-dashed border-gs-tertiary-2 p-8 text-center">
        <p className="text-sm text-gs-secondary-1 mb-4">
          {t("result_not_found")}
        </p>
        <Link
          href={`/${lang}/sites`}
          className="text-sm text-primary hover:text-primary-hover"
        >
          ← {tSites("back_to_sites")}
        </Link>
      </div>
    );
  }
  if (siteError) {
    return (
      <p className="text-sm text-red-600">
        {tCommon("error")}: {siteError}
      </p>
    );
  }
  if (!site || !siteWorkspaceId) return null;

  if (resultQ.loading && !display) {
    return <p className="text-sm text-gs-secondary-1">{tCommon("loading")}</p>;
  }
  if (resultQ.error && !display) {
    const code = (resultQ.error as { status?: number } | null)?.status;
    if (code === 404) {
      return (
        <div className="rounded-md border border-dashed border-gs-tertiary-2 p-8 text-center">
          <p className="text-sm text-gs-secondary-1 mb-4">
            {t("result_not_found")}
          </p>
          <Link
            href={`/${lang}/sites/${siteId}`}
            className="text-sm text-primary hover:text-primary-hover"
          >
            ← {t("back_to_site")}
          </Link>
        </div>
      );
    }
    return (
      <p className="text-sm text-red-600">
        {tCommon("error")}: {resultQ.error.message}
      </p>
    );
  }
  if (!display) return null;

  const overall = toNumber(display.overall_score);
  const rawMetrics = (display.raw_metrics ?? {}) as RawMetrics;
  const insights = (display.insights ?? null) as InsightsBlob | null;
  const improvements = (display.improvements ?? null) as ImprovementsBlob | null;
  const completedDt = display.completed_at
    ? new Date(display.completed_at).toLocaleString(lang)
    : "—";
  const triggeredDt = new Date(display.triggered_at).toLocaleString(lang);
  const durationS =
    display.duration_ms !== null
      ? Math.round(display.duration_ms / 1000)
      : null;

  return (
    <div className="space-y-6">
      <Link
        href={`/${lang}/sites/${siteId}`}
        className="inline-block text-sm text-gs-secondary-1 hover:text-primary"
      >
        ← {t("back_to_site")}
      </Link>

      <header className="rounded-2xl border border-gs-quarterly-1 bg-white p-6">
        <p className="text-xs uppercase tracking-wider text-gs-secondary-2 mb-1">
          {site.type === "own"
            ? tSites("own_sites")
            : tSites("competitor_sites")}
        </p>
        <h1 className="text-xl font-bold text-gs-primary mb-1 truncate">
          {site.nickname || site.domain}
        </h1>
        <a
          href={site.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-primary hover:text-primary-hover break-all"
        >
          {site.url}
        </a>

        <div className="mt-5 flex flex-wrap items-center gap-3">
          <StatusBadge status={display.status} />
          <FundingBadge funding={display.funding_source} />
          <TriggerBadge type={display.trigger_type} />
        </div>

        <dl className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-2 text-sm">
          <dt className="text-gs-secondary-1">{t("triggered_at")}</dt>
          <dd className="text-gs-primary">{triggeredDt}</dd>
          <dt className="text-gs-secondary-1">{t("completed_at")}</dt>
          <dd className="text-gs-primary">{completedDt}</dd>
          {durationS !== null && (
            <>
              <dt className="text-gs-secondary-1">{t("duration")}</dt>
              <dd className="text-gs-primary tabular-nums">
                {t("duration_seconds", { seconds: durationS })}
              </dd>
            </>
          )}
          <dt className="text-gs-secondary-1">{t("version")}</dt>
          <dd className="text-gs-primary">{display.analysis_version}</dd>
        </dl>
      </header>

      {display.status === "failed" && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-5">
          <h2 className="text-sm font-semibold text-red-800 mb-1">
            {t("failed_title")}
          </h2>
          {display.error_message && (
            <p className="text-sm text-red-700 break-words">
              <span className="font-medium">{t("error_message")}:</span>{" "}
              {display.error_message}
            </p>
          )}
        </div>
      )}

      {isActiveStatus(display.status) && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50 p-5">
          <div className="flex items-center gap-3">
            <Spinner />
            <div>
              <h2 className="text-sm font-semibold text-blue-900">
                {t("running_title")}
              </h2>
              <p className="text-sm text-blue-800">
                {display.status === "queued"
                  ? t("queued_subtitle")
                  : t("running_subtitle")}
              </p>
            </div>
          </div>
        </div>
      )}

      {display.status === "completed" && (
        <>
          <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-2xl border border-gs-quarterly-1 bg-white p-6 flex flex-col items-center justify-center">
              <p className="text-xs uppercase tracking-wider text-gs-secondary-2 mb-2">
                {t("overall_score")}
              </p>
              {overall !== null ? (
                <div className="flex items-baseline gap-1">
                  <span className="text-5xl font-bold tabular-nums text-gs-primary">
                    {Math.round(overall)}
                  </span>
                  <span className="text-base text-gs-secondary-1">/100</span>
                </div>
              ) : (
                <p className="text-sm text-gs-secondary-1">{t("no_score")}</p>
              )}
            </div>
            <div className="rounded-2xl border border-gs-quarterly-1 bg-white p-4">
              <RadarChart
                categoryScores={
                  display.category_scores as
                    | Record<string, number | string | null>
                    | null
                    | undefined
                }
                analyzedCategories={display.categories}
              />
            </div>
          </section>

          <section>
            <h2 className="text-xs font-medium text-gs-secondary-1 uppercase tracking-wider mb-3">
              {t("categories_section")}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {ALL_CATEGORIES.map((cat) => {
                const data = rawMetrics[cat] as CategoryMetrics | undefined;
                if (!data) return null;
                return <CategoryCard key={cat} category={cat} data={data} />;
              })}
            </div>
          </section>

          <section>
            <h2 className="text-xs font-medium text-gs-secondary-1 uppercase tracking-wider mb-3">
              {t("insights_section")}
            </h2>
            <InsightsPanel insights={insights} lang={lang} />
          </section>

          <section>
            <h2 className="text-xs font-medium text-gs-secondary-1 uppercase tracking-wider mb-3">
              {t("improvements_section")}
            </h2>
            <ImprovementsList improvements={improvements} lang={lang} />
          </section>
        </>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: AnalysisStatus }) {
  const t = useTranslations("app.sites.status");
  const cls = isActiveStatus(status)
    ? "bg-blue-50 text-blue-700 ring-blue-200"
    : status === "completed"
      ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
      : "bg-red-50 text-red-700 ring-red-200";
  return (
    <span
      className={`inline-flex items-center rounded-pill px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${cls}`}
    >
      {t(status)}
    </span>
  );
}

function FundingBadge({ funding }: { funding: AnalysisFundingSource }) {
  const t = useTranslations("app.sites.results.funding_source");
  return (
    <span className="inline-flex items-center rounded-pill px-2 py-0.5 text-xs font-medium bg-slate-100 text-slate-700 ring-1 ring-inset ring-slate-200">
      {t(funding)}
    </span>
  );
}

function TriggerBadge({ type }: { type: AnalysisTriggerType }) {
  const t = useTranslations("app.sites.results");
  const label =
    type === "manual"
      ? t("trigger_type_manual")
      : type === "scheduled"
        ? t("trigger_type_scheduled")
        : t("trigger_type_monthly_auto");
  return (
    <span className="inline-flex items-center rounded-pill px-2 py-0.5 text-xs font-medium bg-gs-bg-darker text-gs-secondary-1 ring-1 ring-inset ring-gs-quarterly-1">
      {label}
    </span>
  );
}

function Spinner() {
  return (
    <span
      className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-blue-300 border-t-blue-700"
      aria-hidden
    />
  );
}
