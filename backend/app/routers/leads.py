from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.schemas import LeadRequest, LeadResponse
from app.models.tables import AnalysisResult, Lead
from app.services.email_service import send_report_email

router = APIRouter()


@router.post("/lead", response_model=LeadResponse)
async def capture_lead(req: LeadRequest, db: AsyncSession = Depends(get_db)):
    # Verify analysis exists and is completed
    result = await db.execute(
        select(AnalysisResult).where(AnalysisResult.id == req.analysis_id)
    )
    analysis = result.scalar_one_or_none()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if analysis.status != "completed":
        raise HTTPException(status_code=400, detail="Analysis not yet completed")

    # Check for duplicate lead
    existing = await db.execute(
        select(Lead).where(
            Lead.analysis_id == req.analysis_id, Lead.email == req.email
        )
    )
    if existing.scalar_one_or_none():
        return LeadResponse(success=True, message="Report already sent to this email")

    # Create lead
    lead = Lead(analysis_id=req.analysis_id, email=req.email)
    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    # Send email
    try:
        await send_report_email(analysis, req.email)
        lead.report_sent = True
        await db.commit()
    except Exception:
        pass  # Lead captured regardless of email success

    return LeadResponse(success=True)
