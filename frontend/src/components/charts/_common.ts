/**
 * F3 차트 공통 — 5축 색상 팔레트 + 헬퍼.
 *
 * 색상은 `components/analysis/v2/CategoryCard.tsx` 의 `TONE` (gradient) 와
 * 정렬된 단일 색상. recharts `stroke`/`fill` 에 사용.
 */
import type { CategoryName } from "@/lib/api/analyses";

/** 5축 카테고리 색상 (Tailwind 500 톤 기반). */
export const CATEGORY_COLORS: Record<CategoryName, string> = {
  technical: "#3b82f6", // blue-500
  structured: "#8b5cf6", // violet-500
  content: "#f59e0b", // amber-500
  authority: "#f43f5e", // rose-500
  visibility: "#10b981", // emerald-500
};

/** overall_score 라인 색 (강조 — 진한 회색). */
export const OVERALL_COLOR = "#0f172a"; // slate-900

/** ALL_CATEGORIES 와 동일 순서 (radar/legend 순서). */
export const CATEGORY_ORDER: CategoryName[] = [
  "technical",
  "structured",
  "content",
  "authority",
  "visibility",
];

/** ``categories.length < 5`` → 부분 분석 (decision 5: 점 모양 ✕). */
export function isPartialAnalysis(categories: string[]): boolean {
  return categories.length < CATEGORY_ORDER.length;
}

/** Decimal | string | null → number | null (시계열 차트 Y 축). */
export function toScoreNumber(
  v: number | string | null | undefined,
): number | null {
  if (v === null || v === undefined) return null;
  if (typeof v === "number") return Number.isFinite(v) ? v : null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}
