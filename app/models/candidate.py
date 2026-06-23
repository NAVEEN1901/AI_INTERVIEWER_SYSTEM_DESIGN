"""Candidate profile model."""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.db.base import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    headline = Column(String(500), nullable=True)
    summary = Column(Text, nullable=True)
    skills = Column(JSON, default=list)  # ["Python", "ML", "FastAPI"]
    experience_years = Column(Float, default=0.0)
    education = Column(JSON, default=list)  # [{"degree": "...", "institution": "..."}]
    current_company = Column(String(255), nullable=True)
    current_role = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", backref="candidate_profile")
    resumes = relationship("Resume", back_populates="candidate")
