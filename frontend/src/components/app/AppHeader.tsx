"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { createClient } from "@/lib/supabase/client";
import { useActiveWorkspace } from "@/lib/hooks/useActiveWorkspace";
import { useTrialStatus, type TrialStage } from "@/lib/hooks/useTrialStatus";

import { TrialExpiryModal } from "./TrialExpiryModal";

const STAGE_BADGE_CLASS: Record<TrialStage, string> = {
  safe: "bg-emerald-50 text-emerald-700 border-emerald-200",
  warning: "bg-amber-50 text-amber-700 border-amber-200",
  urgent: "bg-red-50 text-red-700 border-red-200",
  expired: "bg-red-50 text-red-700 border-red-200",
  not_trial: "",
};

export function AppHeader({ lang }: { lang: string }) {
  const t = useTranslations("app.nav");
  const tTrial = useTranslations("app.trial.badge");
  const router = useRouter();

  const ws = useActiveWorkspace();
  const trial = useTrialStatus(ws.workspace?.id);

  // shouldShowModal 가 처음 true 가 될 때 1회 모달 open. dismiss 후에는 ❌.
  const [modalOpen, setModalOpen] = useState(false);
  useEffect(() => {
    if (trial.shouldShowModal && !modalOpen) {
      setModalOpen(true);
    }
    // shouldShowModal 가 false 로 바뀌어도 진행 중인 modalOpen 은 닫지 ❌.
  }, [trial.shouldShowModal, modalOpen]);

  async function onLogout() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push(`/${lang}/login`);
  }

  function onModalClose() {
    setModalOpen(false);
    trial.dismissModal();
  }

  return (
    <>
      <header className="sticky top-0 z-50 w-full border-b border-gray-200 bg-white/80 backdrop-blur">
        <nav className="flex items-center justify-between px-5 sm:px-8 min-h-[64px] max-w-shell mx-auto">
          <Link href={`/${lang}/dashboard`} className="flex items-center gap-2">
            <span className="text-lg font-bold tracking-tight">
              AEO <span className="text-primary">Visibility</span>
            </span>
          </Link>
          <div className="flex items-center gap-4 text-sm">
            {trial.showBadge && (
              <TrialBadge
                stage={trial.stage}
                daysRemaining={trial.daysRemaining}
                lang={lang}
                label={
                  trial.stage === "expired"
                    ? tTrial("expired")
                    : tTrial("days_remaining", {
                        days: Math.max(0, trial.daysRemaining ?? 0),
                      })
                }
              />
            )}
            <Link href={`/${lang}/dashboard`} className="hover:text-primary">
              {t("dashboard")}
            </Link>
            <Link href={`/${lang}/sites`} className="hover:text-primary">
              {t("sites")}
            </Link>
            <Link
              href={`/${lang}/settings/workspace`}
              className="hover:text-primary"
            >
              {t("settings")}
            </Link>
            <button onClick={onLogout} className="hover:text-primary">
              {t("logout")}
            </button>
          </div>
        </nav>
      </header>

      <TrialExpiryModal
        open={modalOpen}
        onClose={onModalClose}
        stage={trial.stage}
        daysRemaining={trial.daysRemaining}
        lang={lang}
      />
    </>
  );
}

function TrialBadge({
  stage,
  daysRemaining: _daysRemaining,
  lang,
  label,
}: {
  stage: TrialStage;
  daysRemaining: number | null;
  lang: string;
  label: string;
}) {
  return (
    <Link
      href={`/${lang}/pricing`}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${STAGE_BADGE_CLASS[stage]}`}
      title={label}
    >
      <span aria-hidden="true">●</span>
      <span>{label}</span>
    </Link>
  );
}
