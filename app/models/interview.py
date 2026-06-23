"""Interview model."""

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.db.base import Base


class InterviewType(str, enum.Enum):
    TEXT = "text"
    VOICE = "voice"
    VIDEO = "video"


class InterviewStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    job_application_id = Column(Integer, ForeignKey("job_applications.id"), nullable=False)
    interview_type = Column(Enum(InterviewType), default=InterviewType.TEXT)
    status = Column(Enum(InterviewStatus), default=InterviewStatus.SCHEDULED)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    questions = Column(JSON, default=list)  # AI-generated questions
    responses = Column(JSON, default=list)  # Candidate responses
    transcript = Column(Text, nullable=True)  # For voice interviews
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    application = relationship("JobApplication", backref="interviews")
    evaluation = relationship("Evaluation", back_populates="interview", uselist=False)


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), unique=True, nullable=False)
    overall_score = Column(Float, nullable=False)
    technical_score = Column(Float, nullable=True)
    communication_score = Column(Float, nullable=True)
    problem_solving_score = Column(Float, nullable=True)
    strengths = Column(JSON, default=list)
    weaknesses = Column(JSON, default=list)
    recommendation = Column(String(50), nullable=True)  # hire, reject, maybe
    explanation = Column(Text, nullable=True)  # Explainable AI output
    evaluated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    interview = relationship("Interview", back_populates="evaluation")
