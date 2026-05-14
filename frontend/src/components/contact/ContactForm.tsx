"use client";

/**
 * Contact 폼 — zod + useState (react-hook-form 의존 ❌).
 *
 * 동작:
 *   1. URL ``?topic=demo|sales|support`` 자동 prefill (다른 값은 무시).
 *   2. 클라이언트 zod 검증 → 필드별 에러 + i18n 메시지.
 *   3. submit → POST /api/contact → 200/422/429 분기.
 *   4. honeypot ``website`` 필드는 ``aria-hidden`` + visually hidden — bot 만 채움.
 *
 * 백엔드는 honeypot 채워도 200 OK 위장 응답이라 client UX 차이 ❌.
 * Rate limit 429 만 별도 에러 메시지.
 */
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { z } from "zod";

import {
  submitContact,
  type ContactCreatePayload,
  type ContactTopic,
  ContactError,
} from "@/lib/api/contact";

const VALID_TOPICS: readonly ContactTopic[] = [
  "demo",
  "sales",
  "support",
  "general",
];

interface Props {
  lang: string;
  defaultTopic?: ContactTopic;
}

type Status =
  | { kind: "idle" }
  | { kind: "submitting" }
  | { kind: "success" }
  | { kind: "error"; messageKey: ErrorMessageKey };

type ErrorMessageKey = "rate_limit" | "validation" | "network" | "generic";

interface FieldErrors {
  name?: string;
  email?: string;
  message?: string;
}

export function ContactForm({ lang, defaultTopic }: Props) {
  const t = useTranslations("app.contact");
  const tErr = useTranslations("app.contact.errors");

  const search = useSearchParams();
  const urlTopic = search?.get("topic");
  const initialTopic: ContactTopic = useMemo(() => {
    if (defaultTopic) return defaultTopic;
    if (urlTopic && (VALID_TOPICS as readonly string[]).includes(urlTopic)) {
      return urlTopic as ContactTopic;
    }
    return "general";
  }, [defaultTopic, urlTopic]);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [topic, setTopic] = useState<ContactTopic>(initialTopic);
  const [message, setMessage] = useState("");
  const [website, setWebsite] = useState(""); // honeypot
  const [errors, setErrors] = useState<FieldErrors>({});
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  // URL 변경 시 (e.g. /contact → /contact?topic=demo) 동기화.
  useEffect(() => {
    setTopic(initialTopic);
  }, [initialTopic]);

  // i18n 메시지를 schema 안에서 직접 참조 (refine 마다 재계산).
  const schema = useMemo(
    () =>
      z.object({
        name: z
          .string()
          .trim()
          .min(1, tErr("name_required"))
          .max(200, tErr("name_too_long")),
        email: z
          .string()
          .trim()
          .min(1, tErr("email_required"))
          .email(tErr("email_invalid")),
        company: z.string().trim().max(200, tErr("company_too_long")).optional(),
        topic: z.enum(["demo", "sales", "support", "general"]),
        message: z
          .string()
          .trim()
          .min(1, tErr("message_required"))
          .max(5000, tErr("message_too_long")),
      }),
    [tErr],
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrors({});

    const parsed = schema.safeParse({
      name, email, company: company || undefined, topic, message,
    });
    if (!parsed.success) {
      const next: FieldErrors = {};
      for (const issue of parsed.error.issues) {
        const f = issue.path[0];
        if (f === "name" && !next.name) next.name = issue.message;
        else if (f === "email" && !next.email) next.email = issue.message;
        else if (f === "message" && !next.message) next.message = issue.message;
      }
      setErrors(next);
      setStatus({ kind: "idle" });
      return;
    }

    setStatus({ kind: "submitting" });
    const payload: ContactCreatePayload = {
      name: parsed.data.name,
      email: parsed.data.email,
      company: parsed.data.company || null,
      topic: parsed.data.topic,
      message: parsed.data.message,
      locale: lang,
      website, // honeypot — 정상 사용자는 빈 string.
    };
    try {
      await submitContact(payload);
      setStatus({ kind: "success" });
    } catch (err) {
      let key: ErrorMessageKey = "generic";
      if (err instanceof ContactError) {
        if (err.status === 429) key = "rate_limit";
        else if (err.status === 422) key = "validation";
      } else if (err instanceof TypeError) {
        // fetch 실패 — network.
        key = "network";
      }
      setStatus({ kind: "error", messageKey: key });
    }
  }

  if (status.kind === "success") {
    return <SuccessBox />;
  }

  const submitting = status.kind === "submitting";

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-5 rounded-2xl border border-gray-200 bg-white p-6 sm:p-8 max-w-xl mx-auto"
      noValidate
    >
      {/* honeypot — bot 만 채움. 사용자에겐 숨김. */}
      <div
        aria-hidden="true"
        style={{
          position: "absolute",
          left: "-9999px",
          width: "1px",
          height: "1px",
          overflow: "hidden",
        }}
      >
        <label htmlFor="contact-website">Website (leave blank)</label>
        <input
          id="contact-website"
          type="text"
          tabIndex={-1}
          autoComplete="off"
          value={website}
          onChange={(e) => setWebsite(e.target.value)}
        />
      </div>

      <Field
        id="contact-name"
        label={t("fields.name")}
        error={errors.name}
        required
      >
        <input
          id="contact-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={200}
          autoComplete="name"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:border-gs-primary-1 focus:ring-1 focus:ring-gs-primary-1"
          required
        />
      </Field>

      <Field
        id="contact-email"
        label={t("fields.email")}
        error={errors.email}
        required
      >
        <input
          id="contact-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          maxLength={200}
          autoComplete="email"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:border-gs-primary-1 focus:ring-1 focus:ring-gs-primary-1"
          required
        />
      </Field>

      <Field id="contact-company" label={t("fields.company")}>
        <input
          id="contact-company"
          type="text"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          maxLength={200}
          autoComplete="organization"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:border-gs-primary-1 focus:ring-1 focus:ring-gs-primary-1"
        />
      </Field>

      <Field id="contact-topic" label={t("fields.topic")} required>
        <select
          id="contact-topic"
          value={topic}
          onChange={(e) => setTopic(e.target.value as ContactTopic)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:border-gs-primary-1 focus:ring-1 focus:ring-gs-primary-1 bg-white"
        >
          <option value="general">{t("topics.general")}</option>
          <option value="demo">{t("topics.demo")}</option>
          <option value="sales">{t("topics.sales")}</option>
          <option value="support">{t("topics.support")}</option>
        </select>
      </Field>

      <Field
        id="contact-message"
        label={t("fields.message")}
        error={errors.message}
        required
      >
        <textarea
          id="contact-message"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          maxLength={5000}
          rows={5}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:border-gs-primary-1 focus:ring-1 focus:ring-gs-primary-1 resize-y"
          required
        />
      </Field>

      {status.kind === "error" && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {tErr(status.messageKey)}
        </div>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-lg bg-gs-primary-1 text-white px-4 py-3 text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {submitting ? t("submitting") : t("submit")}
      </button>

      <p className="text-xs text-gs-secondary-1 text-center">
        {t("privacy_note")}
      </p>
    </form>
  );
}

function Field({
  id,
  label,
  required,
  error,
  children,
}: {
  id: string;
  label: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-sm font-medium text-gs-text-1 mb-1.5"
      >
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
      {error && (
        <p className="mt-1 text-xs text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

function SuccessBox() {
  const t = useTranslations("app.contact.success");
  return (
    <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-8 max-w-xl mx-auto text-center">
      <div className="mx-auto h-12 w-12 rounded-full bg-emerald-500 flex items-center justify-center text-white text-2xl font-bold mb-4">
        ✓
      </div>
      <h2 className="text-xl font-bold text-gs-text-1 mb-2">{t("title")}</h2>
      <p className="text-sm text-gs-secondary-1 leading-relaxed">
        {t("description")}
      </p>
    </div>
  );
}
