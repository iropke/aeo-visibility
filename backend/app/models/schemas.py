from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, HttpUrl, field_validator


class AnalyzeRequest(BaseModel):
    url: str
    language: str = "en"

    @field_validator("url")
    @classmethod
    def normalize_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v


class AnalyzeResponse(BaseModel):
    id: UUID
    status: str
    message: str = "Analysis started"


class CategoryDetail(BaseModel):
    score: int
    weight: float = 0.2
    details: dict[str, Any] = {}


class ProgressInfo(BaseModel):
    current_step: str
    steps_completed: int
    total_steps: int = 5


class Recommendation(BaseModel):
    category: str
    priority: str
    title: str
    description: str


class ResultResponse(BaseModel):
    id: UUID
    url: str
    status: str
    overall_score: Optional[int] = None
    grade: Optional[str] = None
    categories: Optional[dict[str, CategoryDetail]] = None
    summary: Optional[str] = None
    recommendations: Optional[list[Recommendation]] = None
    progress: Optional[ProgressInfo] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class LeadRequest(BaseModel):
    analysis_id: UUID
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email address")
        return v


class LeadResponse(BaseModel):
    success: bool
    message: str = "Report will be sent shortly"


class HealthResponse(BaseModel):
    status: str
    redis: str
    db: str
