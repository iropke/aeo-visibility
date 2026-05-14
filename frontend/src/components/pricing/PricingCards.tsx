"use client";

/**
 * Pricing 카드 + 월/연 토글 (client component).
 *
 * server component(`page.tsx`) 가 plans 를 SSR fetch 후 props 로 전달.
 * 본 컴포넌트는 토글 상태만 관리 + i18n 통한 라벨 렌더.
 *
 * 가격 표시:
 *   - monthly toggle = ON → ``$XX.99 / mo`` (price_monthly_usd 그대로)
 *   - annual toggle = ON  → ``$YY.99 / mo billed annually`` (annual / 12 환산)
 *   - annual=NULL 인 free 는 토글 무관 ``Free``
 *
 * Phase 2 쿠폰 적용 가격은 ``listPlans`` 응답 자체가 변경되므로 본 컴포넌트 변경 ❌.
 */
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import type { Plan } from "@/lib/api/plans";
import {
  formatUSD,
  formatUSDPerMonthFromAnnual,
  isUnlimited,
} from "@/lib/format/currency";

type Billing = "monthly" | "annual";
type CardPlanId = "free" | "basic" | "pro" | "business";
type SupportTier =
  | "self"
  | "email"
  | "email_chat"
  | "email_chat_sla4h"
  | "dedicated";

const CARD_PLANS: readonly CardPlanId[] = ["free", "basic", "pro", "business"];
const FEATURED_PLAN_ID: CardPlanId = "pro";

interface Props {
  plans: Plan[];
  lang: string;
}

export function PricingCards({ plans, lang }: Props) {
  const t = useTranslations("app.pricing");
  const [billing, setBilling] = useState<Billing>("monthly");

  const planById = useMemo(() => {
    const m = new Map<string, Plan>();
    for (const p of plans) m.set(p.id, p);
    return m;
  }, [plans]);

  return (
    <div className="space-y-10">
      <div className="flex items-center justify-center gap-3">
        <BillingToggleButton
          active={billing === "monthly"}
          onClick={() => setBilling("monthly")}
        >
          {t("toggle.monthly")}
        </BillingToggleButton>
        <BillingToggleButton
          active={billing === "annual"}
          onClick={() => setBilling("annual")}
        >
          {t("toggle.annual")}
          <span className="ml-2 text-[11px] font-semibold text-emerald-700 bg-emerald-50 rounded-full px-2 py-0.5">
            {t("toggle.annual_save")}
          </span>
        </BillingToggleButton>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {CARD_PLANS.map((id) => {
          const plan = planById.get(id);
          if (!plan) return null;
          return (
            <PlanCard
              key={id}
              plan={plan}
              planId={id}
              billing={billing}
              lang={lang}
              featured={id === FEATURED_PLAN_ID}
            />
          );
        })}
      </div>

      {planById.get("enterprise") && <EnterpriseBox lang={lang} />}
    </div>
  );
}

function BillingToggleButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "px-4 py-2 rounded-full text-sm font-semibold transition-colors",
        active
          ? "bg-gs-primary-1 text-white"
          : "bg-gray-100 text-gray-600 hover:bg-gray-200",
      ].join(" ")}
    >
      {children}
    </button>
  );
}

function PlanCardName({ planId }: { planId: CardPlanId }) {
  const t = useTranslations("app.pricing.plans");
  switch (planId) {
    case "free": return <>{t("free.name")}</>;
    case "basic": return <>{t("basic.name")}</>;
    case "pro": return <>{t("pro.name")}</>;
    case "business": return <>{t("business.name")}</>;
  }
}

function PlanCardTagline({ planId }: { planId: CardPlanId }) {
  const t = useTranslations("app.pricing.plans");
  switch (planId) {
    case "free": return <>{t("free.tagline")}</>;
    case "basic": return <>{t("basic.tagline")}</>;
    case "pro": return <>{t("pro.tagline")}</>;
    case "business": return <>{t("business.tagline")}</>;
  }
}

function SupportLabel({ tier }: { tier: string }) {
  const t = useTranslations("app.pricing.features.support");
  const safeTier: SupportTier =
    tier === "self" || tier === "email" || tier === "email_chat" ||
    tier === "email_chat_sla4h" || tier === "dedicated"
      ? (tier as SupportTier)
      : "self";
  switch (safeTier) {
    case "self": return <>{t("self")}</>;
    case "email": return <>{t("email")}</>;
    case "email_chat": return <>{t("email_chat")}</>;
    case "email_chat_sla4h": return <>{t("email_chat_sla4h")}</>;
    case "dedicated": return <>{t("dedicated")}</>;
  }
}

function PlanCard({
  plan,
  planId,
  billing,
  lang,
  featured,
}: {
  plan: Plan;
  planId: CardPlanId;
  billing: Billing;
  lang: string;
  featured: boolean;
}) {
  const t = useTranslations("app.pricing");
  const monthly = Number(plan.price_monthly_usd);
  const annual = plan.price_annual_usd ? Number(plan.price_annual_usd) : null;

  let priceLabel: string;
  let suffix: string | null;
  if (monthly === 0) {
    priceLabel = t("free");
    suffix = t("trial_duration");
  } else if (billing === "annual" && annual) {
    priceLabel = formatUSDPerMonthFromAnnual(annual, lang);
    suffix = t("per_month_billed_annually");
  } else {
    priceLabel = formatUSD(monthly, lang);
    suffix = t("per_month");
  }

  const unlimited = t("unlimited");
  const fmt = (v: number) => (isUnlimited(v) ? unlimited : String(v));

  return (
    <div
      className={[
        "relative flex flex-col rounded-2xl border p-6 bg-white",
        featured
          ? "border-gs-primary-1 shadow-lg ring-1 ring-gs-primary-1/20"
          : "border-gray-200",
      ].join(" ")}
    >
      {featured && (
        <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-gs-primary-1 text-white text-[11px] font-bold tracking-wider uppercase">
          {t("featured_badge")}
        </span>
      )}

      <h3 className="text-lg font-bold text-gs-text-1">
        <PlanCardName planId={planId} />
      </h3>
      <p className="mt-1 text-sm text-gs-secondary-1 min-h-[2.5rem]">
        <PlanCardTagline planId={planId} />
      </p>

      <div className="mt-4 flex items-baseline gap-1">
        <span className="text-3xl font-bold text-gs-text-1">{priceLabel}</span>
        {suffix && (
          <span className="text-xs text-gs-secondary-1">{suffix}</span>
        )}
      </div>

      <ul className="mt-5 space-y-2 text-sm text-gs-text-1">
        <FeatureItem>
          {t("features.sites", { count: fmt(plan.max_sites) })}
        </FeatureItem>
        <FeatureItem>
          {t("features.competitors_per_site", {
            count: fmt(plan.competitors_per_site),
          })}
        </FeatureItem>
        <FeatureItem>
          {t("features.custom_analyses", {
            count: fmt(plan.custom_analyses_per_month),
          })}
        </FeatureItem>
        <FeatureItem>
          {t("features.timeseries", {
            months: fmt(plan.timeseries_months),
          })}
        </FeatureItem>
        <FeatureItem>
          {t("features.members", {
            count: fmt(plan.max_members_hardcap),
          })}
        </FeatureItem>
        <FeatureItem positive={plan.csv_export}>
          {t("features.csv_export")}
        </FeatureItem>
        <FeatureItem positive={plan.competitor_comparison}>
          {t("features.competitor_comparison")}
        </FeatureItem>
        <FeatureItem positive={plan.industry_benchmark}>
          {t("features.industry_benchmark")}
        </FeatureItem>
        <FeatureItem>
          <SupportLabel tier={plan.support_tier} />
        </FeatureItem>
      </ul>

      <div className="mt-6 pt-6 border-t border-gray-100">
        {planId === "free" ? (
          <Link
            href={`/${lang}/signup`}
            className="block w-full text-center rounded-lg bg-gs-primary-1 text-white px-4 py-2.5 text-sm font-semibold hover:opacity-90 transition-opacity"
          >
            {t("cta.start_trial")}
          </Link>
        ) : (
          <Link
            href={`/${lang}/signup`}
            className={[
              "block w-full text-center rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors",
              featured
                ? "bg-gs-primary-1 text-white hover:opacity-90"
                : "bg-white text-gs-primary-1 border border-gs-primary-1 hover:bg-gs-primary-1/5",
            ].join(" ")}
          >
            {t("cta.choose_plan")}
          </Link>
        )}
      </div>
    </div>
  );
}

function FeatureItem({
  children,
  positive,
}: {
  children: React.ReactNode;
  positive?: boolean;
}) {
  const hasFlag = typeof positive === "boolean";
  const enabled = !hasFlag || positive === true;
  return (
    <li
      className={[
        "flex items-start gap-2",
        enabled ? "text-gs-text-1" : "text-gray-400 line-through",
      ].join(" ")}
    >
      <span
        aria-hidden="true"
        className={[
          "mt-0.5 inline-flex h-4 w-4 items-center justify-center rounded-full text-[10px] flex-shrink-0",
          enabled
            ? "bg-emerald-100 text-emerald-700"
            : "bg-gray-100 text-gray-400",
        ].join(" ")}
      >
        {enabled ? "✓" : "—"}
      </span>
      <span>{children}</span>
    </li>
  );
}

function EnterpriseBox({ lang }: { lang: string }) {
  const t = useTranslations("app.pricing.enterprise");
  return (
    <div className="rounded-2xl border border-gray-200 bg-gradient-to-br from-slate-50 to-white p-8 md:p-10">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
        <div className="md:col-span-2">
          <span className="inline-block px-3 py-1 rounded-full bg-slate-900 text-white text-[11px] font-bold tracking-wider uppercase mb-3">
            {t("badge")}
          </span>
          <h3 className="text-2xl font-bold text-gs-text-1">{t("title")}</h3>
          <p className="mt-2 text-sm text-gs-secondary-1 leading-relaxed">
            {t("description")}
          </p>
          <ul className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2 text-sm text-gs-text-1">
            <FeatureItem>{t("bullet_unlimited")}</FeatureItem>
            <FeatureItem>{t("bullet_dedicated")}</FeatureItem>
            <FeatureItem>{t("bullet_audit")}</FeatureItem>
            <FeatureItem>{t("bullet_sla")}</FeatureItem>
          </ul>
        </div>
        <div className="md:col-span-1 md:text-right">
          <Link
            href={`/${lang}/contact?topic=demo`}
            className="inline-block rounded-lg bg-slate-900 text-white px-5 py-3 text-sm font-semibold hover:bg-slate-700 transition-colors"
          >
            {t("cta")}
          </Link>
        </div>
      </div>
    </div>
  );
}
