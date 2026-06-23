"""Email notification endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.candidate import Candidate
from app.models.job import Job, JobApplication
from app.services.email_service import email_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# --- Schemas ---

class SendShortlistEmail(BaseModel):
    candidate_id: int
    job_id: int


class SendInterviewInvite(BaseModel):
    candidate_id: int
    job_id: int
    interview_type: str = "AI-Powered Interview"
    scheduled_date: str = "TBD"
    duration: int = 30
    interview_link: Optional[str] = None


class BulkNotifyRequest(BaseModel):
    job_id: int
    candidate_ids: list[int]
    notification_type: str  # shortlisted, interview_invite, rejection


# --- Endpoints ---

@router.post("/shortlisted")
def notify_shortlisted(
    payload: SendShortlistEmail,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """Send shortlisting notification email to a candidate."""
    candidate = db.query(Candidate).filter(Candidate.id == payload.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    user = db.query(User).filter(User.id == candidate.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = email_service.send_shortlisted_email(
        to_email=user.email,
        candidate_name=user.full_name,
        job_title=job.title,
        sender_name=current_user.full_name,
    )

    # Update application status
    application = db.query(JobApplication).filter(
        JobApplication.candidate_id == payload.candidate_id,
        JobApplication.job_id == payload.job_id,
    ).first()
    if application:
        application.status = "screening"
        db.commit()

    return result


@router.post("/interview-invite")
def send_interview_invite(
    payload: SendInterviewInvite,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """Send interview invitation email."""
    candidate = db.query(Candidate).filter(Candidate.id == payload.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    user = db.query(User).filter(User.id == candidate.user_id).first()
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not user or not job:
        raise HTTPException(status_code=404, detail="User or Job not found")

    result = email_service.send_interview_invite(
        to_email=user.email,
        candidate_name=user.full_name,
        job_title=job.title,
        interview_type=payload.interview_type,
        scheduled_date=payload.scheduled_date,
        duration=payload.duration,
        interview_link=payload.interview_link,
        sender_name=current_user.full_name,
    )

    # Update application status
    application = db.query(JobApplication).filter(
        JobApplication.candidate_id == payload.candidate_id,
        JobApplication.job_id == payload.job_id,
    ).first()
    if application:
        application.status = "interview"
        db.commit()

    return result


@router.post("/bulk-notify")
def bulk_notify(
    payload: BulkNotifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """Send bulk notifications to multiple candidates."""
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    results = []
    for candidate_id in payload.candidate_ids:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            results.append({"candidate_id": candidate_id, "status": "error", "error": "Not found"})
            continue

        user = db.query(User).filter(User.id == candidate.user_id).first()
        if not user:
            results.append({"candidate_id": candidate_id, "status": "error", "error": "User not found"})
            continue

        if payload.notification_type == "shortlisted":
            result = email_service.send_shortlisted_email(
                to_email=user.email,
                candidate_name=user.full_name,
                job_title=job.title,
                sender_name=current_user.full_name,
            )
        elif payload.notification_type == "rejection":
            result = email_service.send_rejection_email(
                to_email=user.email,
                candidate_name=user.full_name,
                job_title=job.title,
                sender_name=current_user.full_name,
            )
        else:
            result = email_service.send_interview_invite(
                to_email=user.email,
                candidate_name=user.full_name,
                job_title=job.title,
                sender_name=current_user.full_name,
            )

        results.append({"candidate_id": candidate_id, **result})

    return {
        "total": len(payload.candidate_ids),
        "results": results,
    }
