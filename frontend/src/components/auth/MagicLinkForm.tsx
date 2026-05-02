"use client";

import { useTranslations } from "next-intl";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { env } from "@/env";
import { createClient } from "@/lib/supabase/client";

interface Props {
  lang: string;
  /** signup 페이지에서 호출하면 신규 가입 메타데이터를 함께 전달. */
  mode: "login" | "signup";
}

export function MagicLinkForm({ lang, mode }: Props) {
  const t = useTranslations("auth.magic_link_form");
  const router = useRouter();
  const params = useSearchParams();

  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const trimmed = email.trim();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(trimmed)) {
      setError(t("errors.invalid_email"));
      return;
    }

    setSubmitting(true);
    const supabase = createClient();
    const next = params.get("next") || `/${lang}/dashboard`;
    const redirectTo = `${env.NEXT_PUBLIC_SITE_URL}/auth/callback?next=${encodeURIComponent(next)}`;

    const { error: signInError } = await supabase.auth.signInWithOtp({
      email: trimmed,
      options: {
        emailRedirectTo: redirectTo,
        shouldCreateUser: mode === "signup",
      },
    });

    setSubmitting(false);

    if (signInError) {
      setError(t("errors.send_failed"));
      return;
    }

    const verifyUrl = `/${lang}/verify?email=${encodeURIComponent(trimmed)}`;
    router.push(verifyUrl);
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <label htmlFor="email" className="block text-sm font-medium mb-1">
          {t("email_label")}
        </label>
        <input
          id="email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={t("email_placeholder")}
          className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-primary focus:outline-none"
        />
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-md bg-primary text-white font-medium py-2 hover:opacity-90 disabled:opacity-50"
      >
        {submitting ? t("checking") : t("submit")}
      </button>
    </form>
  );
}
