"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { sitesApi, type Site } from "@/lib/api/sites";
import { useApi } from "@/lib/hooks/useApi";
import { useActiveWorkspace } from "@/lib/hooks/useActiveWorkspace";

import { SiteFormModal } from "./SiteFormModal";

export function SitesView({ lang }: { lang: string }) {
  const t = useTranslations("app.sites");
  const tCommon = useTranslations("common");

  const ws = useActiveWorkspace();
  const sitesQ = useApi(
    () => sitesApi.list(ws.workspace!.id),
    [ws.workspace?.id ?? null],
    { enabled: !!ws.workspace },
  );

  const [createOpen, setCreateOpen] = useState(false);

  if (ws.loading) {
    return <p className="text-sm text-gs-secondary-1">{tCommon("loading")}</p>;
  }
  if (ws.error) {
    return (
      <p className="text-sm text-red-600">
        {tCommon("error")}: {ws.error}
      </p>
    );
  }
  if (!ws.workspace) {
    return (
      <div className="rounded-md border border-dashed border-gs-tertiary-2 p-8 text-center">
        <p className="text-sm text-gs-secondary-1 mb-4">
          {t("no_workspace_yet")}
        </p>
        <Link
          href={`/${lang}/onboarding`}
          className="inline-block rounded-md bg-primary text-white font-medium px-4 py-2 hover:bg-primary-hover"
        >
          {t("create_workspace")}
        </Link>
      </div>
    );
  }

  const sites = sitesQ.data ?? [];
  const ownSites = sites.filter((s) => s.type === "own");
  const competitors = sites.filter((s) => s.type === "competitor");

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gs-primary">{t("title")}</h1>
          <p className="text-sm text-gs-secondary-1 mt-1">
            {t("subtitle", { workspace: ws.workspace.name })}
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>{t("add_site")}</Button>
      </div>

      {sitesQ.error && (
        <p className="text-sm text-red-600">
          {tCommon("error")}: {sitesQ.error.message}
        </p>
      )}

      <SitesSection
        title={t("own_sites")}
        emptyText={t("own_empty")}
        sites={ownSites}
        lang={lang}
        loading={sitesQ.loading}
      />
      <SitesSection
        title={t("competitor_sites")}
        emptyText={t("competitors_empty")}
        sites={competitors}
        lang={lang}
        loading={sitesQ.loading}
      />

      <SiteFormModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        workspaceId={ws.workspace.id}
        mode="create"
        onSaved={() => {
          setCreateOpen(false);
          sitesQ.refresh();
        }}
      />
    </div>
  );
}

function SitesSection({
  title,
  emptyText,
  sites,
  lang,
  loading,
}: {
  title: string;
  emptyText: string;
  sites: Site[];
  lang: string;
  loading: boolean;
}) {
  return (
    <section>
      <h2 className="text-xs font-medium text-gs-secondary-1 uppercase tracking-wider mb-3">
        {title}
      </h2>
      {loading && sites.length === 0 ? (
        <p className="text-sm text-gs-secondary-1">…</p>
      ) : sites.length === 0 ? (
        <p className="text-sm text-gs-secondary-2">{emptyText}</p>
      ) : (
        <ul className="divide-y divide-gs-quarterly-1 rounded-md border border-gs-quarterly-1 bg-white">
          {sites.map((site) => (
            <li key={site.id}>
              <Link
                href={`/${lang}/sites/${site.id}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-gs-bg"
              >
                <div className="min-w-0">
                  <p className="font-medium text-gs-primary truncate">
                    {site.nickname || site.domain}
                  </p>
                  <p className="text-xs text-gs-secondary-2 truncate">
                    {site.url}
                  </p>
                </div>
                <span className="ml-4 shrink-0 text-xs text-gs-secondary-2">
                  {site.last_analyzed_at
                    ? new Date(site.last_analyzed_at).toLocaleDateString(lang)
                    : "—"}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
