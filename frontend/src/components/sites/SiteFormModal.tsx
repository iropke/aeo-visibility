"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import {
  sitesApi,
  type Site,
  type SiteCreatePayload,
  type SiteType,
  type SiteUpdatePayload,
} from "@/lib/api/sites";

interface BaseProps {
  open: boolean;
  onClose: () => void;
  workspaceId: string;
  onSaved: () => void;
}

type FormProps =
  | (BaseProps & { mode: "create"; site?: undefined })
  | (BaseProps & { mode: "edit"; site: Site });

export function SiteFormModal(props: FormProps) {
  const t = useTranslations("app.sites.form");
  const tCommon = useTranslations("common");
  const isEdit = props.mode === "edit";

  const [url, setUrl] = useState("");
  const [nickname, setNickname] = useState("");
  const [type, setType] = useState<SiteType>("own");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // open 변화 시 form reset.
  useEffect(() => {
    if (!props.open) return;
    setError(null);
    setSubmitting(false);
    if (isEdit && props.site) {
      setUrl(props.site.url);
      setNickname(props.site.nickname ?? "");
      setType(props.site.type);
    } else {
      setUrl("");
      setNickname("");
      setType("own");
    }
  }, [props.open, isEdit, props.site]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting) return;
    setError(null);

    const trimmedUrl = url.trim();
    if (!trimmedUrl) {
      setError(t("url_required"));
      return;
    }
    const trimmedNick = nickname.trim();

    setSubmitting(true);
    try {
      if (isEdit && props.site) {
        const payload: SiteUpdatePayload = {};
        if (trimmedUrl !== props.site.url) payload.url = trimmedUrl;
        const newNick = trimmedNick === "" ? null : trimmedNick;
        if (newNick !== props.site.nickname) payload.nickname = newNick;

        if (Object.keys(payload).length > 0) {
          await sitesApi.update(props.workspaceId, props.site.id, payload);
        }
      } else {
        const payload: SiteCreatePayload = {
          url: trimmedUrl,
          nickname: trimmedNick || null,
          type,
        };
        await sitesApi.create(props.workspaceId, payload);
      }
      props.onSaved();
    } catch (err) {
      const status = (err as { status?: number }).status;
      const message = err instanceof Error ? err.message : String(err);
      setError(formatBackendError(status, message, t));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open={props.open}
      onClose={props.onClose}
      title={isEdit ? t("title_edit") : t("title_create")}
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gs-primary mb-1">
            {t("url_label")}
          </label>
          <input
            type="url"
            inputMode="url"
            placeholder={t("url_placeholder")}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={submitting}
            required
            className="w-full rounded-md border border-gs-tertiary-2 px-3 py-2 text-sm focus:border-primary focus:outline-none disabled:bg-gs-bg-darker"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gs-primary mb-1">
            {t("nickname_label")}
          </label>
          <input
            type="text"
            placeholder={t("nickname_placeholder")}
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            disabled={submitting}
            maxLength={64}
            className="w-full rounded-md border border-gs-tertiary-2 px-3 py-2 text-sm focus:border-primary focus:outline-none disabled:bg-gs-bg-darker"
          />
        </div>

        {!isEdit && (
          <div>
            <span className="block text-sm font-medium text-gs-primary mb-1">
              {t("type_label")}
            </span>
            <div className="flex gap-3">
              <TypeRadio
                value="own"
                current={type}
                onChange={setType}
                label={t("type_own")}
                description={t("type_own_desc")}
                disabled={submitting}
              />
              <TypeRadio
                value="competitor"
                current={type}
                onChange={setType}
                label={t("type_competitor")}
                description={t("type_competitor_desc")}
                disabled={submitting}
              />
            </div>
          </div>
        )}

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button
            type="button"
            variant="secondary"
            onClick={props.onClose}
            disabled={submitting}
          >
            {tCommon("cancel")}
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? t("saving") : isEdit ? tCommon("save") : t("create")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function TypeRadio({
  value,
  current,
  onChange,
  label,
  description,
  disabled,
}: {
  value: SiteType;
  current: SiteType;
  onChange: (v: SiteType) => void;
  label: string;
  description: string;
  disabled: boolean;
}) {
  const selected = value === current;
  return (
    <label
      className={`flex-1 cursor-pointer rounded-md border p-3 text-sm transition-colors ${
        selected
          ? "border-primary bg-primary/5"
          : "border-gs-tertiary-2 hover:border-gs-secondary-2"
      } ${disabled ? "opacity-50" : ""}`}
    >
      <input
        type="radio"
        name="site_type"
        value={value}
        checked={selected}
        onChange={() => onChange(value)}
        disabled={disabled}
        className="sr-only"
      />
      <span className="block font-medium text-gs-primary">{label}</span>
      <span className="block text-xs text-gs-secondary-1 mt-0.5">
        {description}
      </span>
    </label>
  );
}

/** 백엔드 status 별 사용자-친화 메시지 매핑. */
function formatBackendError(
  status: number | undefined,
  raw: string,
  t: (k: string) => string,
): string {
  switch (status) {
    case 400:
      return t("err_invalid_url");
    case 402:
      return t("err_trial_expired");
    case 403:
      return t("err_plan_limit");
    case 409:
      return t("err_conflict");
    case 429:
      return t("err_url_change_limit");
    default:
      return raw;
  }
}
