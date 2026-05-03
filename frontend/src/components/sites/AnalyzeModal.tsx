"use client";

import { useTranslations } from "next-intl";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import {
  ALL_CATEGORIES,
  analysesApi,
  type CategoryName,
  type PackQuota,
  type QuotaResponse,
} from "@/lib/api/analyses";
import { useApi } from "@/lib/hooks/useApi";

interface Props {
  open: boolean;
  onClose: () => void;
  workspaceId: string;
  siteId: string;
  onTriggered: () => void;
}

export function AnalyzeModal({
  open,
  onClose,
  workspaceId,
  siteId,
  onTriggered,
}: Props) {
  const t = useTranslations("app.sites.analyze");
  const tCommon = useTranslations("common");

  const quotaQ = useApi(() => analysesApi.quota(workspaceId), [workspaceId], {
    enabled: open,
  });

  const [selected, setSelected] = useState<Set<CategoryName>>(
    () => new Set(ALL_CATEGORIES),
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // open 시 reset.
  useEffect(() => {
    if (open) {
      setSelected(new Set(ALL_CATEGORIES));
      setSubmitting(false);
      setError(null);
    }
  }, [open]);

  function toggle(cat: CategoryName) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  }

  const fullScan = selected.size === ALL_CATEGORIES.length;
  const noneSelected = selected.size === 0;

  async function onSubmit() {
    if (submitting || noneSelected) return;
    setError(null);
    setSubmitting(true);
    try {
      await analysesApi.trigger(workspaceId, siteId, {
        categories: fullScan ? null : Array.from(selected),
        allow_payg: false,
      });
      onTriggered();
    } catch (err) {
      const status = (err as { status?: number }).status;
      const raw = err instanceof Error ? err.message : String(err);
      setError(formatTriggerError(status, raw, t));
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={t("title")} size="md">
      <div className="space-y-5">
        <p className="text-sm text-gs-secondary-1">{t("description")}</p>

        <div>
          <span className="block text-sm font-medium text-gs-primary mb-2">
            {t("categories_label")}
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {ALL_CATEGORIES.map((cat) => (
              <CategoryCheckbox
                key={cat}
                category={cat}
                checked={selected.has(cat)}
                onChange={() => toggle(cat)}
                disabled={submitting}
              />
            ))}
          </div>
          {noneSelected && (
            <p className="mt-1.5 text-xs text-red-600">
              {t("select_at_least_one")}
            </p>
          )}
        </div>

        <QuotaPanel
          loading={quotaQ.loading}
          error={quotaQ.error?.message ?? null}
          data={quotaQ.data ?? null}
        />

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={submitting}
          >
            {tCommon("cancel")}
          </Button>
          <Button
            type="button"
            onClick={onSubmit}
            disabled={submitting || noneSelected}
          >
            {submitting
              ? t("triggering")
              : fullScan
                ? t("trigger_full")
                : t("trigger_partial", { n: selected.size })}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function CategoryCheckbox({
  category,
  checked,
  onChange,
  disabled,
}: {
  category: CategoryName;
  checked: boolean;
  onChange: () => void;
  disabled: boolean;
}) {
  const t = useTranslations("app.sites.categories");
  return (
    <label
      className={`flex items-start gap-2 rounded-md border p-2.5 text-sm cursor-pointer transition-colors ${
        checked
          ? "border-primary bg-primary/5"
          : "border-gs-tertiary-2 hover:border-gs-secondary-2"
      } ${disabled ? "opacity-50" : ""}`}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        className="mt-0.5 h-4 w-4 accent-primary"
      />
      <span className="text-gs-primary">{t(category)}</span>
    </label>
  );
}

function QuotaPanel({
  loading,
  error,
  data,
}: {
  loading: boolean;
  error: string | null;
  data: QuotaResponse | null;
}) {
  const t = useTranslations("app.sites.analyze");

  if (loading && !data) {
    return <p className="text-xs text-gs-secondary-2">{t("quota_loading")}</p>;
  }
  if (error) {
    return <p className="text-xs text-red-600">{error}</p>;
  }
  if (!data) return null;

  const rows: Array<{ key: string; pack: PackQuota }> = [
    { key: "pro_pack", pack: data.pro_pack },
    { key: "basic_pack", pack: data.basic_pack },
    { key: "base", pack: data.base },
  ];
  // quota=0 인 pack 은 표시 ❌ (해당 플랜에 적용 안 됨).
  const visible = rows.filter((r) => r.pack.quota !== 0);
  if (visible.length === 0) {
    return (
      <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-900">
        {t("quota_none")}
      </div>
    );
  }

  return (
    <div className="rounded-md border border-gs-quarterly-1 bg-gs-bg-darker px-3 py-2.5">
      <p className="text-xs font-medium text-gs-primary mb-1.5">
        {t("quota_title", { ym: data.year_month })}
      </p>
      <ul className="space-y-1 text-xs">
        {visible.map(({ key, pack }) => (
          <QuotaRow key={key} pack={pack} labelKey={key} />
        ))}
      </ul>
    </div>
  );
}

function QuotaRow({
  pack,
  labelKey,
}: {
  pack: PackQuota;
  labelKey: string;
}) {
  const t = useTranslations("app.sites.analyze");
  const text = useMemo(() => {
    if (pack.quota === -1) return t("quota_unlimited");
    return t("quota_remaining", { remaining: pack.remaining, quota: pack.quota });
  }, [pack, t]);
  return (
    <li className="flex items-center justify-between">
      <span className="text-gs-secondary-1">{t(`pack.${labelKey}`)}</span>
      <span className="font-medium text-gs-primary tabular-nums">{text}</span>
    </li>
  );
}

function formatTriggerError(
  status: number | undefined,
  raw: string,
  t: (k: string) => string,
): string {
  switch (status) {
    case 402:
      return t("err_quota_or_trial");
    case 403:
      return t("err_forbidden");
    case 409:
      return t("err_concurrent");
    case 429:
      return t("err_cooldown");
    default:
      return raw;
  }
}
