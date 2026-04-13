import type { AnalysisResult, AnalyzeResponse } from "@/types/analysis";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error: ${res.status}`);
  }
  return res.json();
}

export async function startAnalysis(url: string, language: string): Promise<AnalyzeResponse> {
  return fetchAPI<AnalyzeResponse>("/analyze", {
    method: "POST",
    body: JSON.stringify({ url, language }),
  });
}

export async function getResult(id: string): Promise<AnalysisResult> {
  return fetchAPI<AnalysisResult>(`/result/${id}`);
}

export async function submitLead(analysisId: string, email: string): Promise<{ success: boolean; message: string }> {
  return fetchAPI("/lead", {
    method: "POST",
    body: JSON.stringify({ analysis_id: analysisId, email }),
  });
}
