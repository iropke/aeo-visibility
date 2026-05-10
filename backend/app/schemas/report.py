"""reports API I/O 스키마."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.report import ReportFormat, ReportStatus


class ReportCreate(BaseModel):
    """POST /workspaces/{ws}/reports 요청 바디."""
    model_config = ConfigDict(extra="forbid")

    analysis_id: UUID | None = Field(
        default=None,
        description=(
            "단일 분석 결과 리포트의 source. None=워크스페이스 종합 리포트(Phase 3)."
        ),
    )
    format: ReportFormat = Field(
        default=ReportFormat.pdf,
        description="다운로드 포맷.",
    )


class ReportResponse(BaseModel):
    """리포트 메타. 목록/단건/POST 응답 모두 동일 shape."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    analysis_id: UUID | None
    format: ReportFormat
    status: ReportStatus
    storage_path: str | None
    file_size_bytes: int | None
    requested_by: UUID
    requested_at: datetime
    completed_at: datetime | None
    error_message: str | None


class ReportDownloadResponse(BaseModel):
    """signed URL 발급 응답.

    Phase 1 stub: ``download_url`` / ``expires_at`` 모두 None — 라우터가
    storage 어댑터 미구현임을 알리는 ``stub: True`` 플래그 동봉.
    Phase 3 에서 실제 Supabase Storage signed URL + 만료 시각 채움.
    """
    report_id: UUID
    format: ReportFormat
    status: ReportStatus
    download_url: str | None = None
    expires_at: datetime | None = None
    stub: bool = Field(
        default=False,
        description="True 면 Phase 1 stub 응답 (실 파일 ❌). Phase 3 에서 False.",
    )
