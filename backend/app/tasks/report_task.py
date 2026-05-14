"""리포트 렌더 태스크 (Phase 1 stub).

Phase 1:
    - POST /reports 직후 BackgroundTasks 가 본 함수 호출.
    - 실 PDF/CSV 렌더 ❌ — pending row 를 ready 로 전이만 (placeholder storage_path).
    - 다운로드 endpoint 는 ``ReportDownloadResponse.stub=True`` 로 응답.

Phase 3 swap:
    - 실 PDF/CSV 렌더 (analysis_results JSONB → 템플릿) + Supabase Storage 업로드.
    - 본 함수 시그니처 보존 — 라우터 계약 / DB 스키마 변경 ❌.
    - 실패 시 status='failed' + error_message.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.report import Report, ReportStatus


log = logging.getLogger(__name__)


# Phase 1 stub: 실 파일 ❌, placeholder size 0.
_STUB_FILE_SIZE_BYTES = 0


def _stub_storage_path(workspace_id: UUID, report_id: UUID, fmt: str) -> str:
    """Supabase Storage 의 미래 위치 — Phase 3 가 동일 path 로 객체 업로드."""
    return f"reports/{workspace_id}/{report_id}.{fmt}"


async def run_report_render(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    report_id: UUID,
    workspace_id: UUID,
) -> None:
    """Phase 1 stub: pending → ready 로 마크 + placeholder 메타 채움.

    호출자는 라우터의 BackgroundTasks. 별도 세션을 열어 짧은 tx 로 UPDATE.
    실패 시 swallow + log — 라우터 응답은 이미 반환되어 있음.
    """
    try:
        async with session_factory() as session:
            report = await session.get(Report, report_id)
            if report is None:
                log.warning("report_task: report not found id=%s", report_id)
                return
            if report.status != ReportStatus.pending:
                # 이미 처리된 row (재시도 / 멱등성).
                log.info(
                    "report_task: skip — status=%s id=%s",
                    report.status.value, report_id,
                )
                return

            now = datetime.now(timezone.utc)
            report.status = ReportStatus.ready
            report.storage_path = _stub_storage_path(
                workspace_id, report_id, report.format.value,
            )
            report.file_size_bytes = _STUB_FILE_SIZE_BYTES
            report.completed_at = now
            await session.commit()
    except Exception:  # noqa: BLE001
        log.exception("report_task: render failed id=%s", report_id)
        # 실패 마킹 — 호출자 응답 영향 ❌.
        try:
            async with session_factory() as session:
                report = await session.get(Report, report_id)
                if report is None or report.status != ReportStatus.pending:
                    return
                report.status = ReportStatus.failed
                report.completed_at = datetime.now(timezone.utc)
                report.error_message = "Phase 1 stub render failed"
                await session.commit()
        except Exception:  # noqa: BLE001
            log.exception(
                "report_task: failure-marking also failed id=%s", report_id,
            )
