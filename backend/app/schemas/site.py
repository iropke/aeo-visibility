"""sites API I/O 스키마."""
from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.models.site import SiteType


def normalize_domain(url: str) -> str:
    """URL에서 host를 추출 → lowercase + ``www.`` 접두 제거.

    SPEC §4-5의 30일 cooldown은 host 단위로 비교하므로 일관된 정규화 필요.
    """
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


class SiteCreate(BaseModel):
    url: HttpUrl
    nickname: str | None = Field(default=None, max_length=64)
    type: SiteType = SiteType.own

    @field_validator("url")
    @classmethod
    def _require_host(cls, v: HttpUrl) -> HttpUrl:
        host = (v.host or "").strip()
        if not host or "." not in host:
            raise ValueError("URL must include a valid host with a TLD")
        return v


class SiteUpdate(BaseModel):
    """PATCH 페이로드. URL/nickname만 변경 가능. type 변경은 ❌ (재등록 필요).

    URL 변경 시 워크스페이스당 월 1회 제약이 라우터에서 검증됨.
    """
    url: HttpUrl | None = None
    nickname: str | None = Field(default=None, max_length=64)


class SiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    url: str
    domain: str
    nickname: str | None
    type: SiteType
    last_analyzed_at: datetime | None
    last_url_changed_at: datetime | None
    deleted_at: datetime | None
    delete_cooldown_until: datetime | None
    created_at: datetime
    updated_at: datetime
