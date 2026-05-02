"""워크스페이스 / 멤버 API I/O 스키마."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.workspace import WorkspaceRole


# ============================================================
# Workspace
# ============================================================


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    primary_language: Literal["en", "ko", "es"] = "en"
    timezone: str = Field(default="UTC", max_length=64)


class WorkspaceUpdate(BaseModel):
    """PATCH 페이로드. 모두 optional, owner/admin만 호출 가능 (라우터에서 강제)."""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    primary_language: Literal["en", "ko", "es"] | None = None
    timezone: str | None = Field(default=None, max_length=64)


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    primary_language: str
    timezone: str
    owner_id: UUID
    plan_id: str
    created_at: datetime
    updated_at: datetime

    # 응답 시점에 호출자의 역할을 함께 포함 (UI에서 권한 분기용).
    role: WorkspaceRole | None = None


# ============================================================
# Workspace Member
# ============================================================


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    user_id: UUID
    role: WorkspaceRole
    invited_by: UUID | None = None
    joined_at: datetime
    # profiles join 결과로 채워짐 (옵션).
    display_name: str | None = None


class MemberRoleUpdate(BaseModel):
    """PATCH /members/{user_id} — owner만 호출 가능."""
    role: WorkspaceRole
