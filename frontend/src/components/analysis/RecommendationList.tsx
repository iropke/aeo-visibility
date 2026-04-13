import type { Recommendation, Dictionary } from "@/types/analysis";

const PRIORITY_COLORS = {
  high: "border-l-red-400 bg-red-50/50",
  medium: "border-l-amber-400 bg-amber-50/50",
  low: "border-l-primary bg-primary/5",
};

export default function RecommendationList({
  recommendations,
  dict,
}: {
  recommendations: Recommendation[];
  dict: Dictionary;
}) {
  return (
    <div className="glass-card p-6 sm:p-8">
      <h2 className="text-lg font-bold mb-1">{dict.recommendations_title}</h2>
      <p className="text-sm text-gs-secondary-2 mb-6">{dict.recommendations_subtitle}</p>

      <div className="space-y-3">
        {recommendations.map((rec, i) => (
          <div
            key={i}
            className={`border-l-4 rounded-r-xl p-4 ${PRIORITY_COLORS[rec.priority]}`}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm font-bold text-gs-primary">{rec.title}</span>
              <span className="text-[10px] font-bold uppercase tracking-wider text-gs-secondary-2 bg-white/60 px-2 py-0.5 rounded-full">
                {dict[`priority_${rec.priority}`]}
              </span>
            </div>
            <p className="text-xs text-gs-secondary-1 leading-relaxed">{rec.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
