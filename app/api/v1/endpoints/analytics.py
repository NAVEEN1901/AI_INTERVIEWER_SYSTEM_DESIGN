"""Analytics & Dashboard endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.services.analytics_service import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics & Dashboard"])


@router.get("/overview")
def get_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """Get high-level recruitment metrics for the dashboard."""
    return analytics_service.get_overview(db)


@router.get("/job-pipeline/{job_id}")
def get_job_pipeline(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """Get hiring pipeline metrics for a specific job."""
    return analytics_service.get_job_pipeline(db, job_id)


@router.get("/skills")
def get_skill_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """Get skill frequency distribution across all candidates."""
    return analytics_service.get_skill_distribution(db)


@router.get("/experience")
def get_experience_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """Get candidate experience level distribution."""
    return analytics_service.get_experience_distribution(db)


@router.get("/funnel")
def get_hiring_funnel(
    days: int = Query(30, description="Number of days to look back"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """Get hiring funnel metrics for the last N days."""
    return analytics_service.get_hiring_funnel(db, days=days)
