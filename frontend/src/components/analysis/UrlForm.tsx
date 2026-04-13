"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { startAnalysis } from "@/lib/api";
import type { Locale, Dictionary } from "@/types/analysis";

export default function UrlForm({ lang, dict }: { lang: Locale; dict: Dictionary }) {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    const trimmed = url.trim();
    if (!trimmed) {
      setError(dict.input_error_empty);
      return;
    }

    // Basic URL validation
    const urlPattern = /^(https?:\/\/)?[\w][\w.-]*\.[a-z]{2,}(\/.*)?$/i;
    if (!urlPattern.test(trimmed)) {
      setError(dict.input_error_invalid);
      return;
    }

    setLoading(true);
    try {
      const result = await startAnalysis(trimmed, lang);
      router.push(`/${lang}/result/${result.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="glass-card-strong p-6 sm:p-8">
      <div className="flex flex-col sm:flex-row gap-3">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder={dict.input_placeholder}
          disabled={loading}
          className="flex-1 min-w-0 px-5 py-4 rounded-[18px] bg-white/60 border border-gs-quarterly-1/40 text-gs-primary text-sm placeholder:text-gs-secondary-2 focus:outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/10 transition-all disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading}
          className="btn-primary px-8 py-4 text-sm whitespace-nowrap"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              {dict.input_analyzing}
            </span>
          ) : (
            dict.input_button
          )}
        </button>
      </div>
      {error && (
        <p className="mt-3 text-sm text-red-500 pl-2">{error}</p>
      )}
    </form>
  );
}
