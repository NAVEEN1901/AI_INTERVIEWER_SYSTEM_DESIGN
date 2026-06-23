"""Re-ranking Service - updates candidate rankings after interview evaluations.

Combines:
- Original match score (from JD matching)
- Interview evaluation score
- Skill match confidence
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.models.job import JobApplication
from app.models.interview import Interview, Evaluation, InterviewStatus
from app.models.candidate import Candidate


class ReRankingService:
    """Re-ranks candidates after interviews using composite scoring."""

    def __init__(
        self,
        match_weight: float = 0.30,
        interview_weight: float = 0.50,
        experience_weight: float = 0.20,
    ):
        self.match_weight = match_weight
        self.interview_weight = interview_weight
        self.experience_weight = experience_weight

    def rerank_candidates(
        self,
        db: Session,
        job_id: int,
    ) -> list[dict]:
        """
        Re-rank all candidates for a job based on interview results.
        
        Scoring:
        - Original match_score (30%)
        - Interview evaluation (50%)
        - Experience bonus (20%)
        """
        applications = db.query(JobApplication).filter(
            JobApplication.job_id == job_id
        ).all()

        ranked_candidates = []

        for app in applications:
            candidate = db.query(Candidate).filter(Candidate.id == app.candidate_id).first()
            if not candidate:
                continue

            # Base match score
            match_score = app.match_score or 0

            # Interview score (if interview completed)
            interview_score = 0
            evaluation = None
            interviews = db.query(Interview).filter(
                Interview.job_application_id == app.id,
                Interview.status == InterviewStatus.COMPLETED,
            ).all()

            if interviews:
                # Get the latest evaluation
                for interview in interviews:
                    eval_obj = db.query(Evaluation).filter(
                        Evaluation.interview_id == interview.id
                    ).first()
                    if eval_obj:
                        evaluation = eval_obj
                        interview_score = eval_obj.overall_score

            # Experience bonus (normalized 0-100)
            exp_score = min(100, (candidate.experience_years or 0) * 10)

            # Composite re-ranked score
            composite = (
                self.match_weight * match_score
                + self.interview_weight * interview_score
                + self.experience_weight * exp_score
            )

            ranked_candidates.append({
                "candidate_id": candidate.id,
                "application_id": app.id,
                "composite_score": round(composite, 2),
                "match_score": round(match_score, 2),
                "interview_score": round(interview_score, 2),
                "experience_score": round(exp_score, 2),
                "recommendation": evaluation.recommendation if evaluation else None,
                "status": app.status,
                "has_interview": bool(interviews),
            })

        # Sort by composite score
        ranked_candidates.sort(key=lambda x: x["composite_score"], reverse=True)

        # Assign ranks
        for i, candidate in enumerate(ranked_candidates, 1):
            candidate["rank"] = i

        return ranked_candidates

    def update_application_scores(
        self,
        db: Session,
        job_id: int,
    ) -> int:
        """Update match_score in job_applications based on re-ranking."""
        rankings = self.rerank_candidates(db, job_id)

        updated = 0
        for ranking in rankings:
            app = db.query(JobApplication).filter(
                JobApplication.id == ranking["application_id"]
            ).first()
            if app:
                app.match_score = ranking["composite_score"]
                updated += 1

        db.commit()
        return updated


# Singleton
reranking_service = ReRankingService()
