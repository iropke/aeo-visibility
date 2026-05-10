"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";

import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import type { TrialStage } from "@/lib/hooks/useTrialStatus";

interface TrialExpiryModalProps {
  open: boolean;
  onClose: () => void;
  stage: TrialStage;
  daysRemaining: number | null;
  lang: string;
}

/** 트라이얼 임박/만료 안내 모달 — `useTrialStatus.shouldShowModal=true` 일 때 표시. */
export function TrialExpiryModal({
  open,
  onClose,
  stage,
  daysRemaining,
  lang,
}: TrialExpiryModalProps) {
  const t = useTranslations("app.trial.modal");
  const tCommon = useTranslations("common");

  if (stage !== "urgent" && stage !== "expired") return null;

  const titleKey = stage === "expired" ? "title_expired" : "title_urgent";
  const bodyKey = stage === "expired" ? "body_expired" : "body_urgent";

  return (
    <Modal open={open} onClose={onClose} title={t(titleKey)} size="sm">
      <div className="space-y-4">
        <p className="text-sm text-gs-secondary-1">
          {stage === "expired"
            ? t(bodyKey)
            : t(bodyKey, { days: Math.max(0, daysRemaining ?? 0) })}
        </p>

        <div className="rounded-lg bg-gs-bg p-4 text-sm text-gs-primary">
          <p className="font-medium mb-1">{t("incentive_title")}</p>
          <p className="text-gs-secondary-1">{t("incentive_body")}</p>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row sm:justify-end sm:gap-3">
          <Button onClick={onClose} variant="ghost">
            {tCommon("cancel")}
          </Button>
          <Link
            href={`/${lang}/pricing`}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            {t("upgrade_cta")}
          </Link>
        </div>
      </div>
    </Modal>
  );
}
