"""Resume schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.resume import ResumeStatus


class ResumeOut(BaseModel):
    id: int
    candidate_id: int
    file_name: str
    file_type: str
    file_size_bytes: Optional[int]
    status: ResumeStatus
    extracted_skills: list[str]
    extracted_experience: list[dict]
    extracted_education: list[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeDetailOut(ResumeOut):
    raw_text: Optional[str] = None
    parsed_data: Optional[dict] = None


class ResumeParsedData(BaseModel):
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    skills: list[str]
    experience_years: float
    education: list[dict]
    word_count: int


class JDMatchRequest(BaseModel):
    job_id: int
    candidate_ids: Optional[list[int]] = None  # None = match all candidates


class JDMatchResult(BaseModel):
    candidate_id: int
    composite_score: float
    skill_match: dict
    experience_match: dict
    text_relevance_score: float
    recommendation: str


class BM25SearchRequest(BaseModel):
    query: str
    top_k: int = 10
