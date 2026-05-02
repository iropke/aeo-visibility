"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import Link from "next/link";

import { workspaceApi, type Workspace, type WorkspaceRole } from "@/lib/api/workspaces";

const ROLE_KEY: Record<WorkspaceRole, string> = {
  owner: "role_owner",
  admin: "role_admin",
  member: "role_member",
  viewer: "role_viewer",
};

export function WorkspaceList({ lang }: { lang: string }) {
  const t = useTranslations("app.dashboard");
  const tCommon = useTranslations("common");

  const [workspaces, setWorkspaces] = useState<Workspace[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    workspaceApi
      .list()
      .then((data) => {
        if (!cancelled) setWorkspaces(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Unknown error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return <p className="text-sm text-red-600">{tCommon("error")}: {error}</p>;
  }

  if (workspaces === null) {
    return <p className="text-sm text-gray-500">{tCommon("loading")}</p>;
  }

  if (workspaces.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-gray-300 p-8 text-center">
        <p className="text-sm text-gray-600 mb-4">{t("no_workspace")}</p>
        <Link
          href={`/${lang}/onboarding`}
          className="inline-block rounded-md bg-primary text-white font-medium px-4 py-2 hover:opacity-90"
        >
          {t("create_workspace")}
        </Link>
      </div>
    );
  }

  return (
    <ul className="divide-y divide-gray-200 rounded-md border border-gray-200">
      {workspaces.map((ws) => (
        <li key={ws.id} className="flex items-center justify-between px-4 py-3">
          <div>
            <p className="font-medium">{ws.name}</p>
            <p className="text-xs text-gray-500">/{ws.slug}</p>
          </div>
          <span className="text-xs uppercase tracking-wider text-gray-500">
            {ws.role ? t(ROLE_KEY[ws.role]) : "—"}
          </span>
        </li>
      ))}
    </ul>
  );
}
