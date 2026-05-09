/**
 * Plans API — 백엔드 `app.routers.plans` 와 매칭.
 *
 * 인증 ❌ public endpoint. Pricing 페이지(server component)에서 fetch 하거나
 * 클라이언트에서 useApi 로 fetch 가능.
 *
 * Phase 2 쿠폰 청크에서 active 쿠폰 적용가를 반환하도록 백엔드 service 1줄 교체.
 * 인터페이스 변경 ❌ — 본 모듈도 그대로.
 */
import { env } from "@/env";

export type PlanId = "free" | "basic" | "pro" | "business" | "enterprise" | string;

export interface Plan {
  id: PlanId;
  name: string;
  price_monthly_usd: string; // Decimal 직렬화 — 표시 시 number 로 변환.
  price_annual_usd: string | null;
  max_sites: number;
  max_competitors: number;
  max_members_default: number;
  max_members_hardcap: number;
  custom_analyses_per_month: number;
  timeseries_months: number;
  csv_export: boolean;
  competitor_comparison: boolean;
  competitor_trend_graph: boolean;
  default_ai_engines: number;
  competitors_per_site: number;
  industry_benchmark: boolean;
  audit_log_days: number;
  data_retention_years: number;
  support_tier: string;
  is_enterprise: boolean;
  is_active: boolean;
}

/**
 * 서버/클라이언트 양쪽에서 사용 가능한 plans fetch.
 *
 * Server component 에서 호출 시 Next.js 자체 fetch 캐싱 적용. 가격은 Phase 2 쿠폰
 * 활성/만료에 따라 변할 수 있으므로 호출자가 ``revalidate`` 로 ISR 주기 결정.
 *
 * 빌드 시점 backend 가 unreachable 일 수 있어 ``listPlansSafe`` 가 try/catch + 빈
 * 배열 폴백 — 페이지 prerender 가 깨지지 않도록 함. 런타임 ISR/revalidate 시
 * 실제 데이터로 갱신.
 */
export async function listPlans(
  options: { revalidate?: number } = {},
): Promise<Plan[]> {
  const url = `${env.NEXT_PUBLIC_BACKEND_URL}/api/plans`;
  const init: RequestInit & { next?: { revalidate?: number } } = {
    headers: { "Content-Type": "application/json" },
  };
  if (typeof options.revalidate === "number") {
    init.next = { revalidate: options.revalidate };
  }
  const res = await fetch(url, init);
  if (!res.ok) {
    throw new Error(`Failed to fetch plans: ${res.status}`);
  }
  return (await res.json()) as Plan[];
}

export async function listPlansSafe(
  options: { revalidate?: number } = {},
): Promise<Plan[]> {
  try {
    return await listPlans(options);
  } catch {
    return [];
  }
}
