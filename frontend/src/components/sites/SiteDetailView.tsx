"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";

import { TimeSeriesChart } from "@/components/charts/TimeSeriesChart";
import { Button } from "@/components/ui/Button";
import {
  analysesApi,
  isActiveStatus,
  type AnalysisResultListItem,
  type AnalysisStatus,
} from "@/lib/api/analyses";
import { sitesApi, type Site } from "@/lib/api/sites";
import {
  resolveSiteWorkspace,
  useActiveWorkspace,
} from "@/lib/hooks/useActiveWorkspace";
import { useApi } from "@/lib/hooks/useApi";

import { AnalyzeModal } from "./AnalyzeModal";
import { SiteFormModal } from "./SiteFormModal";

interface Props {
  lang: string;
  siteId: string;
}

export function SiteDetailView({ lang, siteId }: Props) {
  const t = useTranslations("app.sites");
  const tCommon = useTranslations("common");
  const router = useRouter();

  const ws = useActiveWorkspace();

  // 1) site lookup — 활성 워크스페이스 먼저, 404 면 전체 워크스페이스 순회.
  const [site, setSite] = useState<Site | null>(null);
  const [siteWorkspaceId, setSiteWorkspaceId] = useState<string | null>(null);
  const [siteError, setSiteError] = useState<string | null>(null);
  const [siteLoading, setSiteLoading] = useState(true);
  const [siteRefreshTick, setSiteRefreshTick] = useState(0);

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
        // 활성 워크스페이스에 없음 → 전체 순회 (메일 딥링크 케이스).
        try {
          const resolved = await resolveSiteWorkspace(siteId);
          if (cancelled) return;
          if (resolved === null) {
            setSiteError("not_found");
            setSiteLoading(false);
            return;
          }
          // 활성 워크스페이스 자동 전환.
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
  }, [ws.workspace?.id, siteId, siteRefreshTick]);

  // 2) analyses list — 활성 분석 있으면 2.5초 폴링.
  const activeQ = useApi(
    () => analysesApi.active(siteWorkspaceId!),
    [siteWorkspaceId],
    { enabled: !!siteWorkspaceId, pollIntervalMs: 2500 },
  );
  const hasActiveForThisSite = useMemo(() => {
    if (!activeQ.data) return false;
    return activeQ.data.some((a) => a.site_id === siteId);
  }, [activeQ.data, siteId]);

  const listQ = useApi(
    () => analysesApi.list(siteWorkspaceId!, siteId, { limit: 50 }),
    [siteWorkspaceId, siteId],
    {
      enabled: !!siteWorkspaceId,
      pollIntervalMs: hasActiveForThisSite ? 2500 : 0,
    },
  );

  const [editOpen, setEditOpen] = useState(false);
  const [analyzeOpen, setAnalyzeOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function onDelete() {
    if (!site || !siteWorkspaceId) return;
    if (!window.confirm(t("delete_confirm", { domain: site.domain }))) return;
    setDeleteError(null);
    setDeleting(true);
    try {
      await sitesApi.remove(siteWorkspaceId, site.id);
      router.push(`/${lang}/sites`);
    } catch (err) {
      const status = (err as { status?: number }).status;
      const raw = err instanceof Error ? err.message : String(err);
      setDeleteError(
        status === 402
          ? t("form.err_trial_expired")
          : status === 403
            ? t("delete_forbidden")
            : raw,
      );
      setDeleting(false);
    }
  }

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
        <p className="text-sm text-gs-secondary-1 mb-4">{t("site_not_found")}</p>
        <Link
          href={`/${lang}/sites`}
          className="text-sm text-primary hover:text-primary-hover"
        >
          ← {t("back_to_sites")}
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

  const analyses = listQ.data ?? [];

  return (
    <div className="space-y-8">
      <Link
        href={`/${lang}/sites`}
        className="inline-block text-sm text-gs-secondary-1 hover:text-primary"
      >
        ← {t("back_to_sites")}
      </Link>

      <div className="rounded-2xl border border-gs-quarterly-1 bg-white p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs uppercase tracking-wider text-gs-secondary-2 mb-1">
              {site.type === "own" ? t("own_sites") : t("competitor_sites")}
            </p>
            <h1 className="text-xl font-bold text-gs-primary truncate">
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
          </div>
          <div className="flex shrink-0 gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setEditOpen(true)}
            >
              {tCommon("edit")}
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={onDelete}
              disabled={deleting}
            >
              {deleting ? tCommon("deleting") : tCommon("delete")}
            </Button>
          </div>
        </div>

        {deleteError && (
          <p className="text-sm text-red-600 mt-3">{deleteError}</p>
        )}

        <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
          <dt className="text-gs-secondary-1">{t("last_analyzed")}</dt>
          <dd className="text-gs-primary">
            {site.last_analyzed_at
              ? new Date(site.last_analyzed_at).toLocaleString(lang)
              : "—"}
          </dd>
          <dt className="text-gs-secondary-1">{t("last_url_change")}</dt>
          <dd className="text-gs-primary">
            {site.last_url_changed_at
              ? new Date(site.last_url_changed_at).toLocaleDateString(lang)
              : "—"}
          </dd>
        </dl>

        <div className="mt-5">
          <Button onClick={() => setAnalyzeOpen(true)}>
            {t("run_analysis")}
          </Button>
        </div>
      </div>

      <TimeSeriesChart analyses={analyses} lang={lang} />

      <section>
        <h2 className="text-xs font-medium text-gs-secondary-1 uppercase tracking-wider mb-3">
          {t("analyses_history")}
        </h2>
        {listQ.error && (
          <p className="text-sm text-red-600 mb-3">
            {tCommon("error")}: {listQ.error.message}
          </p>
        )}
        {analyses.length === 0 && !listQ.loading ? (
          <p className="text-sm text-gs-secondary-2">{t("analyses_empty")}</p>
        ) : (
          <ul className="divide-y divide-gs-quarterly-1 rounded-md border border-gs-quarterly-1 bg-white">
            {analyses.map((a) => (
              <AnalysisRow key={a.id} item={a} lang={lang} siteId={siteId} />
            ))}
          </ul>
        )}
      </section>

      <SiteFormModal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        workspaceId={siteWorkspaceId}
        mode="edit"
        site={site}
        onSaved={() => {
          setEditOpen(false);
          setSiteRefreshTick((x) => x + 1);
        }}
      />
      <AnalyzeModal
        open={analyzeOpen}
        onClose={() => setAnalyzeOpen(false)}
        workspaceId={siteWorkspaceId}
        siteId={site.id}
        onTriggered={() => {
          setAnalyzeOpen(false);
          listQ.refresh();
          activeQ.refresh();
        }}
      />
    </div>
  );
}

function AnalysisRow({
  item,
  lang,
  siteId,
}: {
  item: AnalysisResultListItem;
  lang: string;
  siteId: string;
}) {
  const t = useTranslations("app.sites");

  const score =
    item.overall_score === null
      ? "—"
      : typeof item.overall_score === "number"
        ? item.overall_score.toFixed(0)
        : Number(item.overall_score).toFixed(0);

  const triggered = new Date(item.triggered_at).toLocaleString(lang);

  return (
    <li className="flex items-center justify-between px-4 py-3">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <StatusBadge status={item.status} />
          <span className="text-sm text-gs-primary">{triggered}</span>
        </div>
        <p className="text-xs text-gs-secondary-2 mt-0.5">
          {item.categories.map((c) => t(`categories.${c}`)).join(" · ")}
        </p>
      </div>
      <div className="ml-4 flex shrink-0 items-center gap-3">
        <span className="text-base font-semibold text-gs-primary tabular-nums">
          {score}
        </span>
        {item.status === "completed" && (
          <Link
            href={`/${lang}/sites/${siteId}/results/${item.id}`}
            className="text-xs text-primary hover:text-primary-hover"
          >
            {t("view_result")} →
          </Link>
        )}
      </div>
    </li>
  );
}

function StatusBadge({ status }: { status: AnalysisStatus }) {
  const t = useTranslations("app.sites.status");
  const cls = isActiveStatus(status)
    ? "bg-blue-50 text-blue-700"
    : status === "completed"
      ? "bg-emerald-50 text-emerald-700"
      : "bg-red-50 text-red-700";
  return (
    <span
      className={`inline-block rounded-pill px-2 py-0.5 text-xs font-medium ${cls}`}
    >
      {t(status)}
    </span>
  );
}
