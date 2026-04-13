import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(Text, nullable=False)
    domain = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    overall_score = Column(Integer, nullable=True)
    grade = Column(String(2), nullable=True)
    technical_score = Column(Integer, nullable=True)
    technical_details = Column(JSONB, nullable=True)
    structured_score = Column(Integer, nullable=True)
    structured_details = Column(JSONB, nullable=True)
    content_score = Column(Integer, nullable=True)
    content_details = Column(JSONB, nullable=True)
    authority_score = Column(Integer, nullable=True)
    authority_details = Column(JSONB, nullable=True)
    visibility_score = Column(Integer, nullable=True)
    visibility_details = Column(JSONB, nullable=True)
    summary = Column(Text, nullable=True)
    recommendations = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    language = Column(String(5), default="en")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc) + timedelta(days=7),
    )

    leads = relationship("Lead", back_populates="analysis")

    __table_args__ = (Index("idx_analysis_domain", "domain"),)


class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(UUID(as_uuid=True), ForeignKey("analysis_results.id"), nullable=False)
    email = Column(Text, nullable=False)
    report_sent = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    analysis = relationship("AnalysisResult", back_populates="leads")

    __table_args__ = (Index("idx_leads_email", "email"),)
