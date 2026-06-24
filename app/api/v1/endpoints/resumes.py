"""Resume endpoints - Upload, Parse, and JD Matching."""

import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.candidate import Candidate
from app.models.resume import Resume, ResumeStatus
from app.models.job import Job
from app.schemas.resume import (
    ResumeOut,
    ResumeDetailOut,
    JDMatchRequest,
    JDMatchResult,
    BM25SearchRequest,
)
from app.services.resume_parser import parse_resume
from app.services.jd_matcher import jd_matcher, calculate_skill_match_score, calculate_experience_match

router = APIRouter(prefix="/resumes", tags=["Resumes"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


@router.post("/parse-text")
def parse_resume_text(payload: dict):
    """
    Parse resume from raw text (no database required).
    Send: {"text": "resume content here", "filename": "optional.pdf"}
    """
    text = payload.get("text", "")
    if not text or len(text.strip()) < 10:
        raise HTTPException(status_code=400, detail="Please provide resume text (min 10 chars)")

    from app.services.resume_parser import parse_resume_text as _parse_text
    result = _parse_text(text)
    return result


@router.post("/upload", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a resume file (PDF, DOCX, or TXT).
    HR can upload for any candidate; candidates upload their own.
    """
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Supported: {ALLOWED_EXTENSIONS}",
        )

    # Validate file size
    content = await file.read()
    file_size = len(content)
    if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB",
        )

    # Get candidate
    if current_user.role == UserRole.CANDIDATE:
        candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    else:
        # HR uploads - for now, require candidate context (can be extended)
        candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
        if not candidate:
            raise HTTPException(status_code=400, detail="No candidate profile found")

    if not candidate:
        raise HTTPException(status_code=400, detail="Candidate profile not found")

    # Save file
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{candidate.id}_{file.filename}"

    with open(file_path, "wb") as f:
        f.write(content)

    # Create resume record
    resume = Resume(
        candidate_id=candidate.id,
        file_name=file.filename,
        file_path=str(file_path),
        file_type=ext.lstrip("."),
        file_size_bytes=file_size,
        status=ResumeStatus.UPLOADED,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@router.post("/{resume_id}/parse", response_model=ResumeDetailOut)
def parse_uploaded_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Parse an uploaded resume to extract structured data (NLP processing)."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Authorization check
    if current_user.role == UserRole.CANDIDATE:
        candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
        if not candidate or resume.candidate_id != candidate.id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Check file exists
    if not os.path.exists(resume.file_path):
        raise HTTPException(status_code=404, detail="Resume file not found on disk")

    # Parse resume
    resume.status = ResumeStatus.PARSING
    db.commit()

    try:
        parsed = parse_resume(resume.file_path)
        resume.raw_text = parsed["raw_text"]
        resume.parsed_data = {
            "name": parsed["name"],
            "email": parsed["email"],
            "phone": parsed["phone"],
            "word_count": parsed["word_count"],
        }
        resume.extracted_skills = parsed["skills"]
        resume.extracted_experience = [{"years": parsed["experience_years"]}]
        resume.extracted_education = parsed["education"]
        resume.status = ResumeStatus.PARSED

        # Update candidate profile with extracted data
        candidate = db.query(Candidate).filter(Candidate.id == resume.candidate_id).first()
        if candidate:
            candidate.skills = parsed["skills"]
            candidate.experience_years = parsed["experience_years"]
            candidate.education = parsed["education"]

        db.commit()
        db.refresh(resume)
        return resume

    except Exception as e:
        resume.status = ResumeStatus.ERROR
        db.commit()
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")


@router.get("/", response_model=list[ResumeOut])
def list_resumes(
    candidate_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List resumes. Candidates see only their own."""
    query = db.query(Resume)

    if current_user.role == UserRole.CANDIDATE:
        candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
        if not candidate:
            return []
        query = query.filter(Resume.candidate_id == candidate.id)
    elif candidate_id:
        query = query.filter(Resume.candidate_id == candidate_id)

    return query.order_by(Resume.created_at.desc()).all()


@router.get("/{resume_id}", response_model=ResumeDetailOut)
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get resume details including parsed data."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if current_user.role == UserRole.CANDIDATE:
        candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
        if not candidate or resume.candidate_id != candidate.id:
            raise HTTPException(status_code=403, detail="Access denied")

    return resume


@router.post("/match-jd", response_model=list[JDMatchResult])
def match_candidates_to_job(
    payload: JDMatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """
    Match candidates against a Job Description.
    Uses BM25 + skill matching + experience scoring.
    """
    # Get job
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get candidates with parsed resumes
    query = db.query(Resume).filter(Resume.status == ResumeStatus.PARSED)
    if payload.candidate_ids:
        query = query.filter(Resume.candidate_id.in_(payload.candidate_ids))
    resumes = query.all()

    if not resumes:
        raise HTTPException(status_code=404, detail="No parsed resumes found")

    # Match each candidate
    results = []
    for resume in resumes:
        candidate = db.query(Candidate).filter(Candidate.id == resume.candidate_id).first()
        if not candidate:
            continue

        match_result = jd_matcher.match_candidate_to_job(
            candidate_skills=candidate.skills or [],
            candidate_experience=candidate.experience_years or 0,
            candidate_text=resume.raw_text or "",
            job_required_skills=job.required_skills or [],
            job_preferred_skills=job.preferred_skills or [],
            job_description=job.description,
            job_min_experience=job.min_experience_years or 0,
            job_max_experience=job.max_experience_years,
        )

        results.append(JDMatchResult(
            candidate_id=resume.candidate_id,
            **match_result,
        ))

    # Sort by composite score descending
    results.sort(key=lambda x: x.composite_score, reverse=True)
    return results


@router.post("/search", response_model=list[dict])
def bm25_search(
    payload: BM25SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """
    Search candidates using BM25 lexical search.
    Query can be natural language like "Python developer with ML experience".
    """
    # Get all parsed resumes
    resumes = db.query(Resume).filter(Resume.status == ResumeStatus.PARSED).all()
    if not resumes:
        raise HTTPException(status_code=404, detail="No parsed resumes available")

    # Build BM25 index
    documents = [
        {"candidate_id": r.candidate_id, "text": r.raw_text or ""}
        for r in resumes
    ]
    jd_matcher.build_index(documents)

    # Search
    results = jd_matcher.search(payload.query, top_k=payload.top_k)

    # Enrich with candidate info
    enriched = []
    for result in results:
        candidate = db.query(Candidate).filter(Candidate.id == result["candidate_id"]).first()
        if candidate:
            enriched.append({
                **result,
                "name": candidate.user.full_name if candidate.user else None,
                "skills": candidate.skills or [],
                "experience_years": candidate.experience_years,
            })

    return enriched
