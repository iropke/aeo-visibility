"use client";

/**
 * F3 레이더 차트 — 단일 분석의 5축 점수 시각화.
 *
 * 입력: ``analysis_results.category_scores`` (dict[CategoryName, number]).
 * 부분 분석 (5축 미만) 시: 분석된 축만 채우고 나머지는 0으로 표시.
 * 색상: emerald (전체 일관 톤). decision 8 의 카테고리별 색상은 LineChart 에서만 사용.
 *
 * 0~100 도메인 + 4개 그리드. 카테고리 라벨은 i18n (`app.sites.categories.*`).
 */
import { useTranslations } from "next-intl";
import { useMemo } from "react";
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart as RechartsRadar,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

import { ALL_CATEGORIES } from "@/lib/api/analyses";

import { CATEGORY_ORDER, toScoreNumber } from "./_common";

interface Props {
  /** ``raw_metrics`` 또는 ``category_scores`` 중 어느 쪽을 받아도 OK
   * (모두 ``{ technical: 75, ... }`` 형태 — score 만 추출). */
  categoryScores: Record<string, number | string | null> | null | undefined;
  /** 분석된 카테고리 (부분 분석 식별). undefined → 전체로 간주. */
  analyzedCategories?: string[];
}

const RADAR_COLOR = "#10b981"; // emerald-500

export function RadarChart({ categoryScores, analyzedCategories }: Props) {
  const t = useTranslations("app.sites.categories");
  const tC = useTranslations("app.charts");

  const data = useMemo(() => {
    const cs = categoryScores ?? {};
    const analyzed = analyzedCategories
      ? new Set(analyzedCategories)
      : new Set<string>(ALL_CATEGORIES);
    return CATEGORY_ORDER.map((cat) => ({
      category: cat,
      label: t(cat),
      score: analyzed.has(cat)
        ? toScoreNumber(cs[cat] ?? null) ?? 0
        : 0,
      analyzed: analyzed.has(cat),
    }));
  }, [categoryScores, analyzedCategories, t]);

  const hasAny = data.some((d) => d.analyzed);
  if (!hasAny) {
    return (
      <p className="text-sm text-gs-secondary-2">{tC("radar_empty")}</p>
    );
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RechartsRadar data={data} outerRadius="75%">
          <PolarGrid stroke="#cbd5e1" />
          <PolarAngleAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: "#475569" }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: "#94a3b8" }}
            tickCount={5}
          />
          <Radar
            name="score"
            dataKey="score"
            stroke={RADAR_COLOR}
            fill={RADAR_COLOR}
            fillOpacity={0.25}
            strokeWidth={2}
            isAnimationActive={false}
          />
          <Tooltip
            contentStyle={{
              fontSize: 12,
              borderRadius: 8,
              border: "1px solid #e2e8f0",
            }}
            labelStyle={{ color: "#0f172a", fontWeight: 600 }}
            formatter={(v) => [
              typeof v === "number" ? Math.round(v) : String(v),
              tC("radar_value"),
            ]}
          />
        </RechartsRadar>
      </ResponsiveContainer>
    </div>
  );
}

