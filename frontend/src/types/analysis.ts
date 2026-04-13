export interface CategoryDetail {
  score: number;
  weight: number;
  details: Record<string, any>;
}

export interface ProgressInfo {
  current_step: string;
  steps_completed: number;
  total_steps: number;
}

export interface Recommendation {
  category: string;
  priority: "high" | "medium" | "low";
  title: string;
  description: string;
}

export interface AnalysisResult {
  id: string;
  url: string;
  status: "pending" | "processing" | "completed" | "failed";
  overall_score?: number;
  grade?: string;
  categories?: Record<string, CategoryDetail>;
  summary?: string;
  recommendations?: Recommendation[];
  progress?: ProgressInfo;
  created_at?: string;
  completed_at?: string;
}

export interface AnalyzeResponse {
  id: string;
  status: string;
  message: string;
}

export type Locale = "en" | "ko";

export type Dictionary = Record<string, string>;
