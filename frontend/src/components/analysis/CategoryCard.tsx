"use client";

import { useState } from "react";

function scoreColor(score: number): string {
  if (score >= 80) return "#22908b";
  if (score >= 60) return "#5eb6b2";
  if (score >= 40) return "#e6a817";
  if (score >= 20) return "#e67e22";
  return "#e74c3c";
}

function DetailRow({ label, value }: { label: string; value: any }) {
  if (typeof value === "boolean") {
    return (
      <div className="flex justify-between items-center py-1">
        <span className="text-xs text-gs-secondary-1 capitalize">{label.replace(/_/g, " ")}</span>
        <span className={`text-xs font-semibold ${value ? "text-primary" : "text-red-400"}`}>
          {value ? "Yes" : "No"}
        </span>
      </div>
    );
  }
  if (typeof value === "number") {
    return (
      <div className="flex justify-between items-center py-1">
        <span className="text-xs text-gs-secondary-1 capitalize">{label.replace(/_/g, " ")}</span>
        <span className="text-xs font-semibold text-gs-primary">{value}</span>
      </div>
    );
  }
  return null;
}

export default function CategoryCard({
  name,
  description,
  score,
  details,
}: {
  name: string;
  description: string;
  score: number;
  details: Record<string, any>;
}) {
  const [expanded, setExpanded] = useState(false);
  const color = scoreColor(score);

  return (
    <div className="glass-card p-5 h-full flex flex-col">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-bold text-gs-primary mb-1">{name}</h3>
          <p className="text-xs text-gs-secondary-2 leading-relaxed">{description}</p>
        </div>
        <span className="text-2xl font-bold ml-3" style={{ color }}>
          {score}
        </span>
      </div>

      {/* Score bar */}
      <div className="h-2 bg-gs-quarterly-1/40 rounded-full overflow-hidden mb-3">
        <div
          className="h-full rounded-full transition-all duration-1000"
          style={{ width: `${score}%`, background: `linear-gradient(90deg, ${color}, ${color}88)` }}
        />
      </div>

      {/* Expand details */}
      {Object.keys(details).length > 0 && (
        <>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-primary hover:text-primary-hover font-medium mt-auto pt-2 text-left transition-colors"
          >
            {expanded ? "Hide details" : "Show details"}
            <span className="ml-1">{expanded ? "▲" : "▼"}</span>
          </button>

          {expanded && (
            <div className="mt-3 pt-3 border-t border-gs-quarterly-1/30 space-y-0.5">
              {Object.entries(details).map(([key, val]) => {
                if (typeof val === "object" && val !== null && "score" in val) {
                  return (
                    <div key={key} className="flex justify-between items-center py-1.5">
                      <span className="text-xs text-gs-secondary-1 capitalize">
                        {key.replace(/_/g, " ")}
                      </span>
                      <span
                        className="text-xs font-bold"
                        style={{ color: scoreColor(val.score) }}
                      >
                        {val.score}/100
                      </span>
                    </div>
                  );
                }
                return <DetailRow key={key} label={key} value={val} />;
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
