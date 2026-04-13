"use client";

import { useAnalysis } from "@/hooks/useAnalysis";
import type { Locale, Dictionary } from "@/types/analysis";
import AnalysisLoading from "./AnalysisLoading";
import ScoreOverview from "./ScoreOverview";
import CategoryCard from "./CategoryCard";
import RecommendationList from "./RecommendationList";
import EmailCapture from "./EmailCapture";
import Link from "next/link";

const CATEGORY_KEYS = ["technical", "structured", "content", "authority", "visibility"] as const;

export default function ResultView({
  id,
  lang,
  dict,
}: {
  id: string;
  lang: Locale;
  dict: Dictionary;
}) {
  const { data, error } = useAnalysis(id);

  // Loading / polling state
  if (!data || data.status === "pending" || data.status === "processing") {
    return (
      <AnalysisLoading
        dict={dict}
        progress={data?.progress}
      />
    );
  }

  // Error state
  if (data.status === "failed" || error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-center">
        <div className="glass-card p-10 max-w-md">
          <h2 className="text-2xl font-bold mb-3">{dict.error_title}</h2>
          <p className="text-gs-secondary-1 mb-6">
            {data?.summary || error || dict.error_description}
          </p>
          <Link href={`/${lang}`} className="btn-primary">
            {dict.error_retry}
          </Link>
        </div>
      </div>
    );
  }

  // Completed
  return (
    <div className="max-w-4xl mx-auto">
      {/* Score Overview */}
      <div className="text-center mb-10 animate-fade-in-up">
        <p className="text-primary font-bold text-xs tracking-[0.16em] uppercase mb-2">
          {dict.result_title}
        </p>
        <p className="text-gs-secondary-1 text-sm mb-8">{dict.result_subtitle}</p>
        <ScoreOverview
          score={data.overall_score || 0}
          grade={data.grade || "F"}
          dict={dict}
        />
      </div>

      {/* Summary */}
      {data.summary && (
        <div className="glass-card p-6 mb-8 animate-fade-in-up" style={{ animationDelay: "0.15s" }}>
          <p className="text-gs-secondary-1 leading-relaxed text-sm">{data.summary}</p>
        </div>
      )}

      {/* Category Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
        {CATEGORY_KEYS.map((key, i) => (
          <div
            key={key}
            className="animate-fade-in-up"
            style={{ animationDelay: `${0.1 * (i + 2)}s` }}
          >
            <CategoryCard
              name={dict[`cat_${key}`]}
              description={dict[`cat_desc_${key}`]}
              score={data.categories?.[key]?.score || 0}
              details={data.categories?.[key]?.details || {}}
            />
          </div>
        ))}
      </div>

      {/* Recommendations */}
      {data.recommendations && data.recommendations.length > 0 && (
        <div className="mb-10 animate-fade-in-up" style={{ animationDelay: "0.7s" }}>
          <RecommendationList
            recommendations={data.recommendations}
            dict={dict}
          />
        </div>
      )}

      {/* Email Capture */}
      <div className="mb-10 animate-fade-in-up" style={{ animationDelay: "0.8s" }}>
        <EmailCapture analysisId={id} dict={dict} />
      </div>

      {/* New Analysis */}
      <div className="text-center mb-6">
        <Link href={`/${lang}`} className="btn-secondary">
          {dict.new_analysis}
        </Link>
      </div>
    </div>
  );
}
