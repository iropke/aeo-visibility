"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getResult } from "@/lib/api";
import type { AnalysisResult } from "@/types/analysis";

export function useAnalysis(id: string) {
  const [data, setData] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const result = await getResult(id);
        if (cancelled) return;
        setData(result);

        if (result.status === "completed" || result.status === "failed") {
          stopPolling();
        }
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Failed to fetch result");
        stopPolling();
      }
    }

    poll();
    intervalRef.current = setInterval(poll, 2000);

    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [id, stopPolling]);

  return { data, error, isLoading: !data && !error };
}
