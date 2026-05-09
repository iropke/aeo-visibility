"use client";

/**
 * F3 시계열 차트 — overall_score + 5 카테고리 추이.
 *
 * 입력: ``analysesApi.list(workspaceId, siteId, {limit:50})`` 결과 (최신순).
 * 표시: status='completed' 만 (running/queued/failed 점은 차트에서 제외).
 * X 축: triggered_at (오래된 → 최신, lang locale 의 짧은 datetime).
 * Y 축: 0~100.
 * 부분 분석 (categories.length<5): 점 모양 ✕ (decision 5).
 *
 * 라인:
 *   - overall (slate-900, 굵게)
 *   - technical / structured / content / authority / visibility (각 카테고리 색)
 *
 * 결측 값 (부분 분석 시 미분석 카테고리): null → recharts 가 갭으로 표시.
 * connectNulls=true → 갭 건너뛰고 라인 연결 (UX ↑).
 */
import { useTranslations } from "next-intl";
import { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  ALL_CATEGORIES,
  type AnalysisResultListItem,
} from "@/lib/api/analyses";

import {
  CATEGORY_COLORS,
  OVERALL_COLOR,
  isPartialAnalysis,
  toScoreNumber,
} from "./_common";

interface Props {
  analyses: AnalysisResultListItem[];
  lang: string;
}

interface ChartPoint {
  triggered_at: string;
  triggered_at_label: string;
  isPartial: boolean;
  overall: number | null;
  technical: number | null;
  structured: number | null;
  content: number | null;
  authority: number | null;
  visibility: number | null;
}

const Y_TICKS = [0, 25, 50, 75, 100];

export function TimeSeriesChart({ analyses, lang }: Props) {
  const t = useTranslations("app.charts");

  const data: ChartPoint[] = useMemo(() => {
    // completed only + 오래된 순으로 정렬 (X 축).
    const completed = analyses.filter((a) => a.status === "completed");
    const sorted = [...completed].sort(
      (a, b) =>
        new Date(a.triggered_at).getTime() - new Date(b.triggered_at).getTime(),
    );
    const fmt = new Intl.DateTimeFormat(lang, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "numeric",
    });
    return sorted.map((a) => {
      const cs = (a.category_scores ?? {}) as Record<
        string,
        number | string | null
      >;
      return {
        triggered_at: a.triggered_at,
        triggered_at_label: fmt.format(new Date(a.triggered_at)),
        isPartial: isPartialAnalysis(a.categories),
        overall: toScoreNumber(a.overall_score),
        technical: toScoreNumber(cs.technical ?? null),
        structured: toScoreNumber(cs.structured ?? null),
        content: toScoreNumber(cs.content ?? null),
        authority: toScoreNumber(cs.authority ?? null),
        visibility: toScoreNumber(cs.visibility ?? null),
      };
    });
  }, [analyses, lang]);

  if (data.length === 0) {
    return (
      <p className="text-sm text-gs-secondary-2">
        {t("timeseries_empty")}
      </p>
    );
  }

  if (data.length === 1) {
    const only = data[0];
    return (
      <div className="rounded-md border border-gs-quarterly-1 bg-gs-bg p-4 text-sm text-gs-secondary-1">
        {t("timeseries_single_point", {
          score:
            only.overall !== null ? Math.round(only.overall) : 0,
          when: only.triggered_at_label,
        })}
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-gs-quarterly-1 bg-white p-4">
      <h3 className="text-xs font-medium text-gs-secondary-1 uppercase tracking-wider mb-3">
        {t("timeseries_title")}
      </h3>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 8, right: 16, left: 0, bottom: 8 }}
          >
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
            <XAxis
              dataKey="triggered_at_label"
              tick={{ fontSize: 11, fill: "#64748b" }}
              tickMargin={8}
            />
            <YAxis
              domain={[0, 100]}
              ticks={Y_TICKS}
              tick={{ fontSize: 11, fill: "#64748b" }}
              tickMargin={4}
            />
            <Tooltip
              contentStyle={{
                fontSize: 12,
                borderRadius: 8,
                border: "1px solid #e2e8f0",
              }}
              labelStyle={{ color: "#0f172a", fontWeight: 600 }}
              formatter={(v, name) => {
                const n = typeof v === "number" ? Math.round(v) : String(v);
                return [n, t(`legend.${String(name)}`)];
              }}
            />
            <Legend
              wrapperStyle={{ fontSize: 12 }}
              formatter={(value) => t(`legend.${value}`)}
            />
            <Line
              type="monotone"
              dataKey="overall"
              stroke={OVERALL_COLOR}
              strokeWidth={2.5}
              connectNulls
              dot={renderDot(OVERALL_COLOR)}
              activeDot={{ r: 5, stroke: OVERALL_COLOR, strokeWidth: 2 }}
              isAnimationActive={false}
            />
            {ALL_CATEGORIES.map((cat) => (
              <Line
                key={cat}
                type="monotone"
                dataKey={cat}
                stroke={CATEGORY_COLORS[cat]}
                strokeWidth={1.5}
                connectNulls
                dot={renderDot(CATEGORY_COLORS[cat])}
                activeDot={{ r: 4, stroke: CATEGORY_COLORS[cat], strokeWidth: 2 }}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-3 text-xs text-gs-secondary-2">
        {t("timeseries_partial_legend")}
      </p>
    </div>
  );
}

/** 부분 분석 ✕ vs 전체 ◯ 점 (decision 5).
 *
 * recharts 의 `dot` prop 은 `DotType` 을 기대하지만 그 인자 타입(`DotItemDotProps`)이
 * public 으로 export 되지 않아, 각 prop 을 unknown 으로 받아 좁힌다.
 */
function renderDot(color: string) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  function Dot(props: any) {
    const cx = typeof props?.cx === "number" ? props.cx : null;
    const cy = typeof props?.cy === "number" ? props.cy : null;
    const value = props?.value;
    const payload = props?.payload as ChartPoint | undefined;
    if (cx === null || cy === null || value === null || value === undefined) {
      return <g />;
    }
    if (payload?.isPartial) {
      const r = 4;
      return (
        <g aria-hidden>
          <line
            x1={cx - r}
            y1={cy - r}
            x2={cx + r}
            y2={cy + r}
            stroke={color}
            strokeWidth={1.5}
          />
          <line
            x1={cx + r}
            y1={cy - r}
            x2={cx - r}
            y2={cy + r}
            stroke={color}
            strokeWidth={1.5}
          />
        </g>
      );
    }
    return (
      <circle
        cx={cx}
        cy={cy}
        r={3.5}
        fill="white"
        stroke={color}
        strokeWidth={1.5}
      />
    );
  }
  Dot.displayName = "TimeSeriesDot";
  return Dot;
}

