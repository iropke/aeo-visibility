from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import async_session, get_db
from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CategoryDetail,
    ProgressInfo,
    Recommendation,
    ResultResponse,
)
from app.models.tables import AnalysisResult
from app.services.cache import get_cached_result

router = APIRouter()


def normalize_domain(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    domain = domain.lower().removeprefix("www.")
    return domain.split("/")[0].split(":")[0]


async def _run_analysis_background(analysis_id: str):
    """BackgroundTasks에서 실행되는 분석 작업. 자체 DB 세션을 생성."""
    from app.services.analyzer import run_full_analysis

    async with async_session() as db:
        try:
            await run_full_analysis(analysis_id, db)
        except Exception:
            # run_full_analysis 내부에서 이미 status=failed 처리됨
            pass


@router.post("/analyze", response_model=AnalyzeResponse, status_code=202)
async def start_analysis(
    req: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    domain = normalize_domain(req.url)

    # Check cache
    cached_id = await get_cached_result(domain)
    if cached_id:
        return AnalyzeResponse(id=cached_id, status="completed", message="Cached result found")

    # Create analysis record
    analysis = AnalysisResult(url=req.url, domain=domain, language=req.language)
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # Dispatch background task (replaces Celery)
    background_tasks.add_task(_run_analysis_background, str(analysis.id))

    return AnalyzeResponse(id=analysis.id, status="pending")


@router.get("/result/{analysis_id}", response_model=ResultResponse)
async def get_result(analysis_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.id == analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    # Build response
    response = ResultResponse(
        id=analysis.id,
        url=analysis.url,
        status=analysis.status,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
    )

    if analysis.status == "completed":
        response.overall_score = analysis.overall_score
        response.grade = analysis.grade
        response.summary = analysis.summary
        response.recommendations = (
            [Recommendation(**r) for r in analysis.recommendations]
            if analysis.recommendations
            else []
        )
        response.categories = {
            "technical": CategoryDetail(
                score=analysis.technical_score or 0,
                details=analysis.technical_details or {},
            ),
            "structured": CategoryDetail(
                score=analysis.structured_score or 0,
                details=analysis.structured_details or {},
            ),
            "content": CategoryDetail(
                score=analysis.content_score or 0,
                details=analysis.content_details or {},
            ),
            "authority": CategoryDetail(
                score=analysis.authority_score or 0,
                details=analysis.authority_details or {},
            ),
            "visibility": CategoryDetail(
                score=analysis.visibility_score or 0,
                details=analysis.visibility_details or {},
            ),
        }
    elif analysis.status in ("pending", "processing"):
        # Determine progress from which scores are filled
        steps = ["technical", "structured", "content", "authority", "visibility"]
        completed = 0
        current = "technical"
        for step in steps:
            score = getattr(analysis, f"{step}_score", None)
            if score is not None:
                completed += 1
            else:
                current = step
                break
        else:
            current = "visibility"

        response.progress = ProgressInfo(
            current_step=current, steps_completed=completed
        )
    elif analysis.status == "failed":
        response.summary = analysis.error_message or "Analysis failed"

    return response
