"""Semantic Search & Hybrid Search endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.candidate import Candidate
from app.models.resume import Resume, ResumeStatus
from app.models.job import Job
from app.services.hybrid_search import hybrid_search
from app.services.vector_store import vector_store, RESUME_COLLECTION, JOB_COLLECTION
from app.services.embedding_service import generate_embedding, prepare_resume_text_for_embedding

router = APIRouter(prefix="/search", tags=["Search & Ranking"])


# --- Schemas ---

class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 10


class HybridSearchRequest(BaseModel):
    query: str
    required_skills: Optional[list[str]] = None
    top_k: int = 10
    bm25_weight: float = 0.35
    vector_weight: float = 0.45
    skill_weight: float = 0.20


class IndexResumeRequest(BaseModel):
    resume_id: int


class IndexAllRequest(BaseModel):
    """Request to index all parsed resumes."""
    pass


# --- Endpoints ---

@router.post("/semantic")
def semantic_search(
    payload: SemanticSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """
    Semantic search using vector embeddings.
    Finds candidates whose resumes are semantically similar to the query.
    """
    query_embedding = generate_embedding(payload.query)
    results = vector_store.search_similar_resumes(
        query_vector=query_embedding,
        top_k=payload.top_k,
    )

    # Enrich with candidate info
    enriched = []
    for result in results:
        candidate = db.query(Candidate).filter(
            Candidate.id == result["candidate_id"]
        ).first()
        if candidate:
            user = db.query(User).filter(User.id == candidate.user_id).first()
            enriched.append({
                **result,
                "name": user.full_name if user else None,
                "skills": candidate.skills or [],
                "experience_years": candidate.experience_years,
            })

    return enriched


@router.post("/hybrid")
def hybrid_search_endpoint(
    payload: HybridSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """
    Hybrid search combining BM25 (lexical) + Vector (semantic) + Skill matching.
    Provides the best of keyword and meaning-based search.
    """
    # Update weights if custom
    hybrid_search.bm25_weight = payload.bm25_weight
    hybrid_search.vector_weight = payload.vector_weight
    hybrid_search.skill_weight = payload.skill_weight

    results = hybrid_search.search(
        query=payload.query,
        required_skills=payload.required_skills,
        top_k=payload.top_k,
    )

    # Enrich results
    enriched = []
    for result in results:
        candidate = db.query(Candidate).filter(
            Candidate.id == result["candidate_id"]
        ).first()
        if candidate:
            user = db.query(User).filter(User.id == candidate.user_id).first()
            enriched.append({
                **result,
                "name": user.full_name if user else None,
                "skills": candidate.skills or [],
                "experience_years": candidate.experience_years,
            })

    return enriched


@router.post("/index-resume")
def index_single_resume(
    payload: IndexResumeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """Index a single parsed resume into the vector store."""
    resume = db.query(Resume).filter(
        Resume.id == payload.resume_id,
        Resume.status == ResumeStatus.PARSED,
    ).first()

    if not resume:
        raise HTTPException(status_code=404, detail="Parsed resume not found")

    candidate = db.query(Candidate).filter(Candidate.id == resume.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    point_id = hybrid_search.index_candidate(
        candidate_id=candidate.id,
        resume_id=resume.id,
        skills=candidate.skills or [],
        experience_years=candidate.experience_years or 0,
        raw_text=resume.raw_text or "",
    )

    # Update resume with embedding reference
    resume.embedding_id = point_id
    db.commit()

    return {
        "status": "indexed",
        "resume_id": resume.id,
        "candidate_id": candidate.id,
        "embedding_id": point_id,
    }


@router.post("/index-all")
def index_all_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """Index all parsed resumes into the vector store (batch operation)."""
    resumes = db.query(Resume).filter(Resume.status == ResumeStatus.PARSED).all()

    if not resumes:
        raise HTTPException(status_code=404, detail="No parsed resumes found")

    indexed = 0
    errors = []

    for resume in resumes:
        candidate = db.query(Candidate).filter(Candidate.id == resume.candidate_id).first()
        if not candidate:
            errors.append(f"Resume {resume.id}: candidate not found")
            continue

        try:
            point_id = hybrid_search.index_candidate(
                candidate_id=candidate.id,
                resume_id=resume.id,
                skills=candidate.skills or [],
                experience_years=candidate.experience_years or 0,
                raw_text=resume.raw_text or "",
            )
            resume.embedding_id = point_id
            indexed += 1
        except Exception as e:
            errors.append(f"Resume {resume.id}: {str(e)}")

    db.commit()

    return {
        "status": "completed",
        "indexed": indexed,
        "total": len(resumes),
        "errors": errors,
    }


@router.get("/vector-stats")
def get_vector_stats(
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """Get vector store statistics."""
    return {
        "resumes": vector_store.get_collection_info(RESUME_COLLECTION),
        "jobs": vector_store.get_collection_info(JOB_COLLECTION),
    }
