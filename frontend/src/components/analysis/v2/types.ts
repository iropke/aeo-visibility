/**
 * F2 분석 결과 디테일 페이지 타입 — `AnalysisResultDetail.raw_metrics` /
 * `insights` / `improvements` 의 narrowing.
 *
 * 백엔드 단일 소스: `backend/app/scoring/schemas.py` + `services/llm_synthesizer.py`.
 * 변경 시 동기화 필요. extra='forbid' 모델 그대로 미러.
 */

export type CategoryName =
  | "technical"
  | "structured"
  | "content"
  | "authority"
  | "visibility";

export type MetricValue = boolean | number | string | null;

export interface MetricResult {
  key: string;
  display_name_key: string;
  description_key: string;
  value: MetricValue;
  weight: number;
  passed: boolean;
  threshold?: number | null;
  evidence?: string | null;
}

export interface CategoryMetrics {
  score: number;
  metrics: MetricResult[];
}

/** raw_metrics JSONB 형식 — `{ category_name: CategoryMetrics }`. */
export type RawMetrics = Partial<Record<CategoryName, CategoryMetrics>>;

export type ImprovementPriority = "high" | "medium" | "low";
export type ImprovementEffort = "low" | "medium" | "high";

export interface Improvement {
  priority: ImprovementPriority;
  category: CategoryName;
  title_key: string;
  /** lang(en/ko/...) → 설명. synthesizer 가 en/ko/es 만 채우는 시점 — 그 외 lang 은 'en' 폴백. */
  description: Record<string, string>;
  estimated_impact: number;
  estimated_effort: ImprovementEffort;
  related_metric_keys: string[];
}

export interface InsightsBlob {
  /** lang → 한 단락 요약. */
  summary?: Record<string, string>;
  primary_language?: string;
  synthesized_by?: string;
  category_count?: number;
  improvements_count?: number;
  high_priority_capped?: boolean;
  fallback_reason?: string;
}

/** improvements JSONB 형식 — `{ items: Improvement[] }`. */
export interface ImprovementsBlob {
  items?: Improvement[];
}

/** lang(현재 표시 lang) → description fallback to 'en' to ''. */
export function pickDescription(
  description: Record<string, string> | undefined | null,
  lang: string,
): string {
  if (!description) return "";
  return description[lang] ?? description.en ?? "";
}

/** category_scores: dict[str, Decimal | str | int] → number. */
export function toNumber(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  if (typeof v === "number") return Number.isFinite(v) ? v : null;
  if (typeof v === "string") {
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  }
  return null;
}
