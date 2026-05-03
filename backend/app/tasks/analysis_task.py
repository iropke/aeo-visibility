"""분석 실행 태스크 — 5축 카테고리 호출 + LLM 합성 + DB 갱신.

흐름:
    1. analysis_results row를 status='running' 으로 UPDATE.
    2. 선택된 카테고리들의 ``analyze(url, options)`` 를 ``asyncio.gather`` 병렬 호출.
    3. ``compute_overall_score`` 로 가중평균(부분 분석 정규화).
    4. ``llm_synthesizer.synthesize`` 로 insights + improvements 생성.
    5. analysis_results를 status='completed' + 점수/메트릭/insights/improvements UPDATE.
    6. sites.last_analyzed_at = NOW() UPDATE.

실패 시: status='failed' + error_message 저장. 라우터로 예외 전파 ❌ (이미 commit된
analysis row를 사용자가 status로 확인 가능).

Phase 1 G3:
    - 라우터에서 ``await run_analysis(...)`` 동기 호출 (동시성 1).
    - G4에서 ``BackgroundTasks.add_task(run_analysis, ...)`` 로 분리.
    - 카테고리 모듈은 모두 stub → 실제 HTTP 요청 ❌, 빠르게 완료.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.analysis_result import AnalysisResult, AnalysisStatus
from app.models.site import Site
from app.models.workspace import Workspace
from app.scoring import (
    ANALYSIS_VERSION,
    CATEGORY_MODULES,
    AnalysisOptions,
    CategoryMetrics,
    CategoryName,
    compute_overall_score,
)
from app.services.email_service import send_analysis_complete_email
from app.services.llm_synthesizer import synthesize


log = logging.getLogger(__name__)


async def _run_one_category(
    cat: CategoryName, url: str, options: AnalysisOptions
) -> tuple[CategoryName, CategoryMetrics]:
    """단일 카테고리 호출 + 결과 dict 항목 반환. 실패는 호출자에서 raise."""
    module = CATEGORY_MODULES[cat]
    result: CategoryMetrics = await module.analyze(url, options)  # type: ignore[attr-defined]
    return cat, result


async def run_analysis(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    analysis_id: UUID,
    site_id: UUID,
    workspace_id: UUID,
    site_url: str,
    categories: Iterable[CategoryName],
    options: AnalysisOptions | None = None,
) -> None:
    """분석 실행 — 카테고리 병렬 분석 + DB 갱신 (status running → completed/failed).

    호출자(라우터)가 이미 status='queued' analysis_result row를 INSERT한 뒤 호출.
    이 함수는 자체 세션을 열어 별도 트랜잭션에서 UPDATE 수행 — 호출자 트랜잭션과 분리.
    """
    cats = tuple(categories)
    if not cats:
        raise ValueError("categories must be non-empty")

    opts = options or AnalysisOptions()
    started_at = datetime.now(timezone.utc)

    # 1) status='running' UPDATE (별도 짧은 tx).
    async with session_factory() as session:
        await session.execute(
            update(AnalysisResult)
            .where(AnalysisResult.id == analysis_id)
            .values(status=AnalysisStatus.running)
        )
        await session.commit()

    try:
        # 2) 카테고리 병렬 호출.
        results = await asyncio.gather(
            *[_run_one_category(cat, site_url, opts) for cat in cats]
        )
        category_metrics: dict[CategoryName, CategoryMetrics] = dict(results)

        # 3) overall_score (부분 분석 정규화).
        category_scores = {cat: cm.score for cat, cm in category_metrics.items()}
        overall = compute_overall_score(category_scores)

        # 4) LLM 합성 — 워크스페이스 primary_language 조회 후 synthesize 호출.
        async with session_factory() as session:
            ws = await session.scalar(
                select(Workspace).where(Workspace.id == workspace_id)
            )
            primary_language = ws.primary_language if ws else "en"

        insights, improvements = await synthesize(
            category_metrics, primary_language=primary_language
        )

        # 5) 완료 UPDATE (별도 tx).
        completed_at = datetime.now(timezone.utc)
        duration_ms = max(0, int((completed_at - started_at).total_seconds() * 1000))

        async with session_factory() as session:
            await session.execute(
                update(AnalysisResult)
                .where(AnalysisResult.id == analysis_id)
                .values(
                    status=AnalysisStatus.completed,
                    completed_at=completed_at,
                    duration_ms=duration_ms,
                    overall_score=overall,
                    category_scores=category_scores,
                    raw_metrics={
                        cat: cm.model_dump(mode="json")
                        for cat, cm in category_metrics.items()
                    },
                    insights=insights,
                    improvements={"items": [imp.model_dump(mode="json") for imp in improvements]},
                    analysis_version=ANALYSIS_VERSION,
                )
            )
            # 6) sites.last_analyzed_at 갱신.
            await session.execute(
                update(Site)
                .where(Site.id == site_id)
                .values(last_analyzed_at=completed_at)
            )
            await session.commit()

        # 7) 분석 완료 메일 (best-effort) — owner+admin+analyzed_by, 수신자별 lang.
        # 별도 짧은 tx 로 SELECT (analysis row + site row 재조회 → 최신 상태로 발송).
        try:
            async with session_factory() as session:
                fresh_analysis = await session.scalar(
                    select(AnalysisResult).where(AnalysisResult.id == analysis_id)
                )
                fresh_site = await session.scalar(
                    select(Site).where(Site.id == site_id)
                )
                if fresh_analysis is not None and fresh_site is not None:
                    summary = await send_analysis_complete_email(
                        session, analysis=fresh_analysis, site=fresh_site,
                    )
                    log.info(
                        "analysis %s email summary: sent=%s skipped=%s total=%s",
                        analysis_id,
                        summary.get("sent"), summary.get("skipped"), summary.get("total"),
                    )
        except Exception:  # noqa: BLE001
            # 메일 실패가 분석 결과 status 를 바꾸지 ❌. log 만.
            log.exception(
                "analysis %s email send raised — analysis row remains completed",
                analysis_id,
            )

    except Exception as exc:  # noqa: BLE001
        log.exception("analysis %s failed", analysis_id)
        async with session_factory() as session:
            await session.execute(
                update(AnalysisResult)
                .where(AnalysisResult.id == analysis_id)
                .values(
                    status=AnalysisStatus.failed,
                    completed_at=datetime.now(timezone.utc),
                    error_message=str(exc)[:1000],
                )
            )
            await session.commit()
        # 라우터로 전파 ❌ — analysis row.status 로 사용자가 확인.
