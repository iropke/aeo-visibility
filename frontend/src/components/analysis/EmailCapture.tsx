"use client";

import { useState } from "react";
import { submitLead } from "@/lib/api";
import type { Dictionary } from "@/types/analysis";

export default function EmailCapture({
  analysisId,
  dict,
}: {
  analysisId: string;
  dict: Dictionary;
}) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !email.includes("@")) return;

    setStatus("sending");
    try {
      await submitLead(analysisId, email.trim());
      setStatus("sent");
    } catch {
      setStatus("error");
    }
  }

  if (status === "sent") {
    return (
      <div className="glass-card-strong p-8 text-center">
        <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
          <svg className="w-7 h-7 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <p className="text-sm font-semibold text-primary">{dict.email_success}</p>
      </div>
    );
  }

  return (
    <div className="glass-card-strong p-6 sm:p-8">
      <div className="text-center mb-6">
        <h2 className="text-lg font-bold mb-2">{dict.email_title}</h2>
        <p className="text-sm text-gs-secondary-1">{dict.email_description}</p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={dict.email_placeholder}
          disabled={status === "sending"}
          className="flex-1 min-w-0 px-5 py-3.5 rounded-[18px] bg-white/60 border border-gs-quarterly-1/40 text-gs-primary text-sm placeholder:text-gs-secondary-2 focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/10 transition-all disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={status === "sending" || !email.trim()}
          className="btn-primary px-6 py-3.5 text-sm whitespace-nowrap"
        >
          {status === "sending" ? dict.email_sending : dict.email_submit}
        </button>
      </form>

      {status === "error" && (
        <p className="text-center text-sm text-red-500 mt-3">{dict.email_error}</p>
      )}
    </div>
  );
}
