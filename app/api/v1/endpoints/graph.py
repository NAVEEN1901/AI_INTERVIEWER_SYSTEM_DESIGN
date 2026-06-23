"""Knowledge Graph & Graph RAG endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.candidate import Candidate
from app.models.job import Job
from app.services.knowledge_graph import knowledge_graph
from app.services.graph_rag import graph_rag_service

router = APIRouter(prefix="/graph", tags=["Knowledge Graph & Graph RAG"])


# --- Schemas ---

class AddSkillRequest(BaseModel):
    name: str
    category: str = "general"


class AddRelationshipRequest(BaseModel):
    skill1: str
    skill2: str
    relationship: str = "RELATED_TO"


class GraphEvaluationRequest(BaseModel):
    candidate_id: int
    job_id: int


class SkillRecommendationRequest(BaseModel):
    candidate_id: int
    job_id: int


# --- Endpoints ---

@router.get("/status")
def get_graph_status(
    current_user: User = Depends(get_current_user),
):
    """Get knowledge graph status and statistics."""
    return knowledge_graph.get_skill_graph_summary()


@router.get("/related-skills/{skill}")
def get_related_skills(
    skill: str,
    depth: int = 2,
    current_user: User = Depends(get_current_user),
):
    """
    Get skills related to a given skill using graph traversal.
    Works with Neo4j or fallback rule-based graph.
    """
    results = knowledge_graph.get_related_skills(skill, depth=depth)
    return {
        "skill": skill,
        "related": results,
        "total": len(results),
    }


@router.post("/add-skill")
def add_skill(
    payload: AddSkillRequest,
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """Add a skill to the knowledge graph."""
    knowledge_graph.add_skill(payload.name, payload.category)
    return {"status": "added", "skill": payload.name, "category": payload.category}


@router.post("/add-relationship")
def add_relationship(
    payload: AddRelationshipRequest,
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """Create a relationship between two skills in the graph."""
    knowledge_graph.add_skill_relationship(
        payload.skill1, payload.skill2, payload.relationship
    )
    return {
        "status": "created",
        "from": payload.skill1,
        "to": payload.skill2,
        "relationship": payload.relationship,
    }


@router.post("/index-candidate/{candidate_id}")
def index_candidate_in_graph(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """Index a candidate's skills in the knowledge graph."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    knowledge_graph.add_candidate_skills(candidate_id, candidate.skills or [])
    return {
        "status": "indexed",
        "candidate_id": candidate_id,
        "skills_indexed": len(candidate.skills or []),
    }


@router.post("/index-job/{job_id}")
def index_job_in_graph(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """Index a job's skill requirements in the knowledge graph."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    knowledge_graph.add_job_requirements(job_id, job.required_skills or [], job.preferred_skills or [])
    return {
        "status": "indexed",
        "job_id": job_id,
        "required_skills": len(job.required_skills or []),
        "preferred_skills": len(job.preferred_skills or []),
    }


@router.post("/skill-gap")
def analyze_skill_gap(
    payload: GraphEvaluationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """
    Analyze skill gap between a candidate and job using graph traversal.
    Identifies matched skills, missing skills, and transferable skills.
    """
    candidate = db.query(Candidate).filter(Candidate.id == payload.candidate_id).first()
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not candidate or not job:
        raise HTTPException(status_code=404, detail="Candidate or Job not found")

    result = knowledge_graph.get_skill_gap(payload.candidate_id, payload.job_id)

    # If Neo4j unavailable, use direct comparison with graph context
    if result.get("status") == "unavailable":
        graph_context = graph_rag_service.retrieve_graph_context(
            candidate_skills=candidate.skills or [],
            job_required_skills=job.required_skills or [],
            job_preferred_skills=job.preferred_skills or [],
        )
        result = {
            "matched_skills": list(set(s.lower() for s in (candidate.skills or [])) & set(s.lower() for s in (job.required_skills or []))),
            "missing_skills": graph_context["skill_gaps"],
            "transferable_skills": graph_context["transferable_skills"],
        }

    return {
        "candidate_id": payload.candidate_id,
        "job_id": payload.job_id,
        **result,
    }


@router.post("/evaluate")
def graph_rag_evaluation(
    payload: GraphEvaluationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """
    Graph RAG evaluation - combines graph context with AI evaluation.
    Uses knowledge graph traversal to enrich candidate assessment.
    """
    candidate = db.query(Candidate).filter(Candidate.id == payload.candidate_id).first()
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not candidate or not job:
        raise HTTPException(status_code=404, detail="Candidate or Job not found")

    evaluation = graph_rag_service.generate_enhanced_evaluation(
        candidate_skills=candidate.skills or [],
        candidate_experience=candidate.experience_years or 0,
        job_title=job.title,
        job_required_skills=job.required_skills or [],
        job_preferred_skills=job.preferred_skills or [],
    )

    return {
        "candidate_id": payload.candidate_id,
        "job_id": payload.job_id,
        "job_title": job.title,
        "evaluation": evaluation,
    }


@router.post("/recommendations")
def get_skill_recommendations(
    payload: SkillRecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get skill-based recommendations using graph traversal.
    Identifies learning path and transferable skills.
    """
    candidate = db.query(Candidate).filter(Candidate.id == payload.candidate_id).first()
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not candidate or not job:
        raise HTTPException(status_code=404, detail="Candidate or Job not found")

    recommendations = graph_rag_service.get_skill_recommendations(
        candidate_skills=candidate.skills or [],
        job_required_skills=job.required_skills or [],
    )

    return {
        "candidate_id": payload.candidate_id,
        "job_id": payload.job_id,
        **recommendations,
    }
