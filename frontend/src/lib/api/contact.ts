/**
 * Contact API — 백엔드 `app.routers.contact` 와 매칭.
 *
 * 인증 ❌ public endpoint. Honeypot + IP rate limit 은 백엔드에서 처리.
 *
 * 응답 status:
 *   200 OK              — 저장 성공 (또는 honeypot 통과 후 위장 응답)
 *   422 Unprocessable   — Pydantic 검증 실패 (email/length 등)
 *   429 Too Many Requests — IP rate limit 초과
 */
"use client";

import { env } from "@/env";

export type ContactTopic = "demo" | "sales" | "support" | "general";

export interface ContactCreatePayload {
  name: string;
  email: string;
  company?: string | null;
  topic?: ContactTopic;
  message: string;
  locale?: string;
  /** Honeypot — 항상 빈 문자열로 보냄 (bot 만 채움). */
  website?: string;
}

export interface ContactResponse {
  ok: boolean;
  message: string;
}

export class ContactError extends Error {
  status: number;
  payload: unknown;
  constructor(status: number, payload: unknown, message: string) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

export async function submitContact(
  payload: ContactCreatePayload,
): Promise<ContactResponse> {
  const res = await fetch(`${env.NEXT_PUBLIC_BACKEND_URL}/api/contact`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const text = await res.text();
  const parsed = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const message =
      (parsed && typeof parsed === "object" && "detail" in parsed
        ? String((parsed as { detail: unknown }).detail)
        : null) || `Submission failed: ${res.status}`;
    throw new ContactError(res.status, parsed, message);
  }

  return parsed as ContactResponse;
}
