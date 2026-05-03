/**
 * 작은 fetch + cancel + refresh 헬퍼 — Phase 1 의 임시 캐싱-없음 패턴.
 *
 * 결정 C (entry memo): TanStack Query 도입 보류 (의존성 ❌). 본 훅은 setInterval
 * polling 과 결합하는 단일 진입점. 워크스페이스/사이트/분석 등 거의 모든 클라이언트
 * 페이지가 이 훅을 통해 데이터 가져옴.
 *
 * 폴링 인터벌이 필요한 곳은 `pollIntervalMs` 옵션으로 동작 — 0 또는 미설정이면
 * 일회성. document.hidden 이면 자동 일시정지 후 visibilitychange 시 재개.
 */
"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface ApiState<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
  /** 강제 재요청. 인터벌 폴링과 무관하게 바로 fetch 트리거. */
  refresh: () => void;
}

export interface UseApiOptions {
  /** ms 단위. 0 또는 undefined = 폴링 ❌. */
  pollIntervalMs?: number;
  /** false 면 fetch 자체를 건너뜀 (의존성 미준비 등). 기본 true. */
  enabled?: boolean;
}

export function useApi<T>(
  fn: () => Promise<T>,
  deps: ReadonlyArray<unknown>,
  opts: UseApiOptions = {},
): ApiState<T> {
  const { pollIntervalMs = 0, enabled = true } = opts;

  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState<boolean>(enabled);
  const [tick, setTick] = useState(0);

  // fn 은 매 렌더마다 새 reference 일 수 있으므로 ref 로 가두기.
  const fnRef = useRef(fn);
  fnRef.current = fn;

  const refresh = useCallback(() => {
    setTick((t) => t + 1);
  }, []);

  // 1) 본 fetch (의존성/refresh 시 한 번).
  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    fnRef
      .current()
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setError(null);
        setLoading(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e : new Error(String(e)));
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick, enabled, ...deps]);

  // 2) 폴링 — pollIntervalMs > 0 일 때만. document.hidden 시 일시정지.
  useEffect(() => {
    if (!enabled || pollIntervalMs <= 0) return;

    let intervalId: ReturnType<typeof setInterval> | null = null;
    const start = () => {
      if (intervalId !== null) return;
      intervalId = setInterval(() => {
        setTick((t) => t + 1);
      }, pollIntervalMs);
    };
    const stop = () => {
      if (intervalId === null) return;
      clearInterval(intervalId);
      intervalId = null;
    };

    const onVisibility = () => {
      if (document.hidden) stop();
      else start();
    };

    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", onVisibility);
      if (!document.hidden) start();
    } else {
      start();
    }

    return () => {
      stop();
      if (typeof document !== "undefined") {
        document.removeEventListener("visibilitychange", onVisibility);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pollIntervalMs, enabled, ...deps]);

  return { data, error, loading, refresh };
}
