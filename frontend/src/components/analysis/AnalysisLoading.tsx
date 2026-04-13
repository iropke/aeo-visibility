"use client";

import type { Dictionary, ProgressInfo } from "@/types/analysis";

const STEPS = ["technical", "structured", "content", "authority", "visibility"];

function StepIcon({ status }: { status: "done" | "active" | "pending" }) {
  if (status === "done") {
    return (
      <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      </div>
    );
  }
  if (status === "active") {
    return (
      <div className="w-8 h-8 rounded-full border-2 border-primary bg-primary/10 flex items-center justify-center">
        <div className="w-3 h-3 rounded-full bg-primary animate-pulse-dot" />
      </div>
    );
  }
  return (
    <div className="w-8 h-8 rounded-full border-2 border-gs-quarterly-1 bg-white flex items-center justify-center">
      <div className="w-2 h-2 rounded-full bg-gs-tertiary-2" />
    </div>
  );
}

export default function AnalysisLoading({
  dict,
  progress,
}: {
  dict: Dictionary;
  progress?: ProgressInfo;
}) {
  const completed = progress?.steps_completed || 0;
  const currentStep = progress?.current_step || "technical";

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <div className="glass-card-strong p-8 sm:p-12 max-w-lg w-full text-center">
        {/* Spinner */}
        <div className="mb-8">
          <svg className="animate-spin h-12 w-12 mx-auto text-primary" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
            <path className="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>

        <h2 className="text-xl font-bold mb-2">{dict.loading_title}</h2>
        <p className="text-gs-secondary-1 text-sm mb-8">{dict.loading_subtitle}</p>

        {/* Steps */}
        <div className="space-y-4 text-left">
          {STEPS.map((step, i) => {
            let status: "done" | "active" | "pending" = "pending";
            if (i < completed) status = "done";
            else if (step === currentStep || i === completed) status = "active";

            const stepKey = `step_${step}` as keyof typeof dict;

            return (
              <div key={step} className="flex items-center gap-3">
                <StepIcon status={status} />
                <span
                  className={`text-sm font-medium transition-colors ${
                    status === "done"
                      ? "text-primary"
                      : status === "active"
                      ? "text-gs-primary"
                      : "text-gs-secondary-2"
                  }`}
                >
                  {dict[stepKey]}
                </span>
              </div>
            );
          })}
        </div>

        {/* Progress bar */}
        <div className="mt-8 h-1.5 bg-gs-quarterly-1/50 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-primary to-primary-hover rounded-full transition-all duration-700"
            style={{ width: `${(completed / 5) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}
