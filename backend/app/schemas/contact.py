"""Contact 폼 API I/O 스키마.

라우터: ``app.routers.contact`` (POST /api/contact, public 인증 ❌).
DB 모델: ``app.models.contact_submission.ContactSubmission``.

검증 규칙:
    - name      : 1~200 chars, trim
    - email     : Pydantic ``EmailStr`` (RFC 5322 호환)
    - company   : 0~200 chars, optional
    - topic     : ENUM (demo/sales/support/general), 기본 general
    - message   : 1~5000 chars, trim
    - locale    : 2~10 chars (en/ko/zh-Hant 등), 기본 en
    - website   : honeypot — 비어있어야 통과 (spam bot 감지). 응답에는 미포함.

i18n 메시지 매핑은 frontend ``app.contact.errors.*`` 키 → backend detail string.
백엔드는 영어 detail string 만 반환, frontend 가 status 코드/필드명으로 lookup.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.contact_submission import ContactTopic


class ContactCreate(BaseModel):
    """POST /api/contact 페이로드."""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    company: str | None = Field(default=None, max_length=200)
    topic: ContactTopic = ContactTopic.general
    message: str = Field(min_length=1, max_length=5000)
    locale: str = Field(default="en", min_length=2, max_length=10)
    # honeypot — bot 이 모든 input 채우는 동작 감지. 정상 사용자는 hidden 필드라 비움.
    website: str | None = Field(default=None, max_length=500)

    @field_validator("company")
    @classmethod
    def _empty_company_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class ContactResponse(BaseModel):
    """POST /api/contact 응답 — 최소 정보만 (id 노출 ❌, 어뷰저 추적 회피)."""
    ok: bool = True
    message: str = "Submission received."
