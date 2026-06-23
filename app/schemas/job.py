"""Job schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.job import JobStatus


class JobCreate(BaseModel):
    title: str
    description: str
    department: Optional[str] = None
    location: Optional[str] = None
    employment_type: str = "full_time"
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    min_experience_years: float = 0.0
    max_experience_years: Optional[float] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None


class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    required_skills: Optional[list[str]] = None
    preferred_skills: Optional[list[str]] = None
    min_experience_years: Optional[float] = None
    max_experience_years: Optional[float] = None
    status: Optional[JobStatus] = None


class JobOut(BaseModel):
    id: int
    title: str
    description: str
    department: Optional[str]
    location: Optional[str]
    employment_type: str
    required_skills: list[str]
    preferred_skills: list[str]
    min_experience_years: float
    max_experience_years: Optional[float]
    salary_min: Optional[int]
    salary_max: Optional[int]
    status: JobStatus
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


class JobApplicationCreate(BaseModel):
    job_id: int


class JobApplicationOut(BaseModel):
    id: int
    job_id: int
    candidate_id: int
    status: str
    match_score: Optional[float]
    applied_at: datetime

    model_config = {"from_attributes": True}
