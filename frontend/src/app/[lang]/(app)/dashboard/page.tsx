import { getTranslations, setRequestLocale } from "next-intl/server";

import { isLocale } from "@/lib/i18n/config";
import { WorkspaceList } from "@/components/app/WorkspaceList";

export default async function DashboardPage({
  params,
}: {
  params: Promise<{ lang: string }>;
}) {
  const { lang } = await params;
  if (!isLocale(lang)) return null;
  setRequestLocale(lang);

  const t = await getTranslations("app.dashboard");

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t("title")}</h1>
      <section>
        <h2 className="text-sm font-medium text-gray-700 uppercase tracking-wider mb-3">
          {t("your_workspaces")}
        </h2>
        <WorkspaceList lang={lang} />
      </section>
    </div>
  );
}
