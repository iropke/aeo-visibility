"use client";

import { useEffect, useState } from "react";
import type { Dictionary } from "@/types/analysis";

const GRADE_COLORS: Record<string, string> = {
  A: "#22908b",
  B: "#5eb6b2",
  C: "#e6a817",
  D: "#e67e22",
  F: "#e74c3c",
};

const GRADE_KEYS: Record<string, string> = {
  A: "grade_a",
  B: "grade_b",
  C: "grade_c",
  D: "grade_d",
  F: "grade_f",
};

export default function ScoreOverview({
  score,
  grade,
  dict,
}: {
  score: number;
  grade: string;
  dict: Dictionary;
}) {
  const [animatedScore, setAnimatedScore] = useState(0);
  const color = GRADE_COLORS[grade] || GRADE_COLORS.C;
  const gradeLabel = dict[GRADE_KEYS[grade] || "grade_c"];

  // Animate score counter
  useEffect(() => {
    let frame: number;
    const duration = 1500;
    const start = performance.now();

    function animate(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      setAnimatedScore(Math.round(eased * score));
      if (progress < 1) frame = requestAnimationFrame(animate);
    }

    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [score]);

  // SVG circle parameters
  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (animatedScore / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Circular gauge */}
      <div className="relative w-44 h-44">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 160 160">
          {/* Background circle */}
          <circle
            cx="80"
            cy="80"
            r={radius}
            fill="none"
            stroke="#e8e8ec"
            strokeWidth="10"
          />
          {/* Score circle */}
          <circle
            cx="80"
            cy="80"
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 1.5s cubic-bezier(0.22,1,0.36,1)" }}
          />
        </svg>
        {/* Center content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-bold" style={{ color }}>
            {animatedScore}
          </span>
          <span className="text-xs text-gs-secondary-2 uppercase tracking-wider">/100</span>
        </div>
      </div>

      {/* Grade badge */}
      <div className="flex items-center gap-2">
        <span
          className="inline-flex items-center justify-center w-10 h-10 rounded-full text-white text-lg font-bold"
          style={{ backgroundColor: color }}
        >
          {grade}
        </span>
        <span className="text-sm font-medium text-gs-secondary-1">{gradeLabel}</span>
      </div>
    </div>
  );
}
