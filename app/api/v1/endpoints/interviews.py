"""Interview & AI Evaluation endpoints."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.candidate import Candidate
from app.models.job import Job, JobApplication
from app.models.interview import Interview, Evaluation, InterviewType, InterviewStatus
from app.services.question_generator import generate_interview_questions
from app.services.evaluation_service import evaluate_interview
from app.services.reranking_service import reranking_service

router = APIRouter(prefix="/interviews", tags=["Interviews & Evaluation"])


# --- Schemas ---

class GenerateQuestionsRequest(BaseModel):
    job_application_id: int
    num_questions: int = 8
    difficulty: str = "mixed"  # easy, medium, hard, mixed


class SubmitResponsesRequest(BaseModel):
    interview_id: int
    responses: list[dict]  # [{"question_id": 1, "response": "..."}]


class EvaluateRequest(BaseModel):
    interview_id: int


class ReRankRequest(BaseModel):
    job_id: int


# --- Endpoints ---

@router.post("/generate-questions")
def generate_questions(
    payload: GenerateQuestionsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """
    Generate AI-powered interview questions personalized for a candidate + job.
    Uses prompt engineering with context augmentation.
    """
    # Get application, job, and candidate
    application = db.query(JobApplication).filter(
        JobApplication.id == payload.job_application_id
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == application.job_id).first()
    candidate = db.query(Candidate).filter(Candidate.id == application.candidate_id).first()
    if not job or not candidate:
        raise HTTPException(status_code=404, detail="Job or Candidate not found")

    # Generate questions
    questions_data = generate_interview_questions(
        job_title=job.title,
        job_description=job.description,
        required_skills=job.required_skills or [],
        preferred_skills=job.preferred_skills or [],
        min_experience=job.min_experience_years or 0,
        max_experience=job.max_experience_years,
        candidate_skills=candidate.skills or [],
        candidate_experience=candidate.experience_years or 0,
        candidate_education=candidate.education or [],
        num_questions=payload.num_questions,
        difficulty=payload.difficulty,
    )

    # Create interview record
    interview = Interview(
        job_application_id=application.id,
        interview_type=InterviewType.TEXT,
        status=InterviewStatus.SCHEDULED,
        questions=questions_data["questions"],
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    return {
        "interview_id": interview.id,
        "questions": questions_data["questions"],
        "candidate_id": candidate.id,
        "job_title": job.title,
    }


@router.post("/submit-responses")
def submit_responses(
    payload: SubmitResponsesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Submit candidate responses to interview questions.
    Can be submitted by the candidate or by HR on behalf.
    """
    interview = db.query(Interview).filter(Interview.id == payload.interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Authorization: candidate can only submit their own
    if current_user.role == UserRole.CANDIDATE:
        application = db.query(JobApplication).filter(
            JobApplication.id == interview.job_application_id
        ).first()
        candidate = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
        if not application or not candidate or application.candidate_id != candidate.id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Update interview with responses
    interview.responses = payload.responses
    interview.status = InterviewStatus.COMPLETED
    interview.started_at = interview.started_at or datetime.now(timezone.utc)
    interview.completed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "status": "responses_submitted",
        "interview_id": interview.id,
        "responses_count": len(payload.responses),
    }


@router.post("/evaluate")
def evaluate_interview_endpoint(
    payload: EvaluateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """
    AI-powered evaluation of interview responses.
    Generates scores, strengths, weaknesses, and explainable recommendation.
    """
    interview = db.query(Interview).filter(
        Interview.id == payload.interview_id,
        Interview.status == InterviewStatus.COMPLETED,
    ).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Completed interview not found")

    if not interview.responses:
        raise HTTPException(status_code=400, detail="No responses to evaluate")

    # Get job info
    application = db.query(JobApplication).filter(
        JobApplication.id == interview.job_application_id
    ).first()
    job = db.query(Job).filter(Job.id == application.job_id).first()

    # Combine questions and responses for evaluation
    questions_and_responses = []
    questions = interview.questions or []
    responses = interview.responses or []

    response_map = {r.get("question_id"): r.get("response", "") for r in responses}

    for q in questions:
        questions_and_responses.append({
            "id": q.get("id"),
            "question": q.get("question", ""),
            "response": response_map.get(q.get("id"), ""),
            "category": q.get("category", "technical"),
            "expected_answer_points": q.get("expected_answer_points", []),
        })

    # Run evaluation
    eval_result = evaluate_interview(
        job_title=job.title if job else "Unknown",
        required_skills=job.required_skills if job else [],
        questions_and_responses=questions_and_responses,
    )

    # Save evaluation
    existing_eval = db.query(Evaluation).filter(
        Evaluation.interview_id == interview.id
    ).first()

    if existing_eval:
        # Update existing
        existing_eval.overall_score = eval_result["overall_score"]
        existing_eval.technical_score = eval_result.get("technical_score")
        existing_eval.communication_score = eval_result.get("communication_score")
        existing_eval.problem_solving_score = eval_result.get("problem_solving_score")
        existing_eval.strengths = eval_result.get("overall_strengths", [])
        existing_eval.weaknesses = eval_result.get("overall_weaknesses", [])
        existing_eval.recommendation = eval_result.get("recommendation")
        existing_eval.explanation = eval_result.get("explanation")
        existing_eval.evaluated_at = datetime.now(timezone.utc)
    else:
        # Create new
        evaluation = Evaluation(
            interview_id=interview.id,
            overall_score=eval_result["overall_score"],
            technical_score=eval_result.get("technical_score"),
            communication_score=eval_result.get("communication_score"),
            problem_solving_score=eval_result.get("problem_solving_score"),
            strengths=eval_result.get("overall_strengths", []),
            weaknesses=eval_result.get("overall_weaknesses", []),
            recommendation=eval_result.get("recommendation"),
            explanation=eval_result.get("explanation"),
        )
        db.add(evaluation)

    db.commit()

    return {
        "interview_id": interview.id,
        "evaluation": eval_result,
    }


@router.post("/rerank")
def rerank_candidates(
    payload: ReRankRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.HR, UserRole.ADMIN)),
):
    """
    Re-rank candidates for a job based on interview evaluations.
    Combines match score + interview score + experience.
    """
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    rankings = reranking_service.rerank_candidates(db, payload.job_id)

    # Also update the stored scores
    updated = reranking_service.update_application_scores(db, payload.job_id)

    return {
        "job_id": payload.job_id,
        "job_title": job.title,
        "total_candidates": len(rankings),
        "scores_updated": updated,
        "rankings": rankings,
    }


@router.get("/{interview_id}")
def get_interview(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get interview details including questions and evaluation."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Get evaluation if exists
    evaluation = db.query(Evaluation).filter(
        Evaluation.interview_id == interview.id
    ).first()

    return {
        "id": interview.id,
        "status": interview.status.value,
        "interview_type": interview.interview_type.value,
        "questions": interview.questions,
        "responses": interview.responses,
        "scheduled_at": interview.scheduled_at,
        "completed_at": interview.completed_at,
        "evaluation": {
            "overall_score": evaluation.overall_score,
            "technical_score": evaluation.technical_score,
            "communication_score": evaluation.communication_score,
            "problem_solving_score": evaluation.problem_solving_score,
            "strengths": evaluation.strengths,
            "weaknesses": evaluation.weaknesses,
            "recommendation": evaluation.recommendation,
            "explanation": evaluation.explanation,
        } if evaluation else None,
    }


@router.get("/by-application/{application_id}")
def get_interviews_by_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all interviews for a job application."""
    interviews = db.query(Interview).filter(
        Interview.job_application_id == application_id
    ).all()

    return [
        {
            "id": i.id,
            "status": i.status.value,
            "interview_type": i.interview_type.value,
            "questions_count": len(i.questions) if i.questions else 0,
            "completed_at": i.completed_at,
        }
        for i in interviews
    ]
