"""Analytics Service - generates recruitment analytics and dashboard data."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User, UserRole
from app.models.candidate import Candidate
from app.models.job import Job, JobApplication, JobStatus
from app.models.resume import Resume, ResumeStatus
from app.models.interview import Interview, Evaluation, InterviewStatus


class AnalyticsService:
    """Generates recruitment analytics data for dashboards."""

    def get_overview(self, db: Session) -> dict:
        """Get high-level recruitment metrics."""
        return {
            "total_candidates": db.query(Candidate).count(),
            "total_jobs": db.query(Job).count(),
            "open_jobs": db.query(Job).filter(Job.status == JobStatus.OPEN).count(),
            "total_applications": db.query(JobApplication).count(),
            "total_resumes": db.query(Resume).count(),
            "parsed_resumes": db.query(Resume).filter(Resume.status == ResumeStatus.PARSED).count(),
            "total_interviews": db.query(Interview).count(),
            "completed_interviews": db.query(Interview).filter(
                Interview.status == InterviewStatus.COMPLETED
            ).count(),
        }

    def get_job_pipeline(self, db: Session, job_id: int) -> dict:
        """Get pipeline metrics for a specific job."""
        applications = db.query(JobApplication).filter(JobApplication.job_id == job_id).all()

        pipeline = {
            "total_applicants": len(applications),
            "stages": {
                "applied": 0,
                "screening": 0,
                "interview": 0,
                "offered": 0,
                "rejected": 0,
            },
            "avg_match_score": 0,
            "top_candidates": [],
        }

        scores = []
        for app in applications:
            stage = app.status or "applied"
            if stage in pipeline["stages"]:
                pipeline["stages"][stage] += 1
            if app.match_score:
                scores.append(app.match_score)

        if scores:
            pipeline["avg_match_score"] = round(sum(scores) / len(scores), 2)

        # Top candidates by match score
        top_apps = sorted(
            [a for a in applications if a.match_score],
            key=lambda x: x.match_score,
            reverse=True,
        )[:5]

        for app in top_apps:
            candidate = db.query(Candidate).filter(Candidate.id == app.candidate_id).first()
            if candidate:
                user = db.query(User).filter(User.id == candidate.user_id).first()
                pipeline["top_candidates"].append({
                    "candidate_id": candidate.id,
                    "name": user.full_name if user else "Unknown",
                    "match_score": app.match_score,
                    "status": app.status,
                })

        return pipeline

    def get_skill_distribution(self, db: Session) -> dict:
        """Get skill frequency distribution across all candidates."""
        candidates = db.query(Candidate).filter(Candidate.skills.isnot(None)).all()

        skill_count: dict[str, int] = {}
        for candidate in candidates:
            if candidate.skills:
                for skill in candidate.skills:
                    skill_lower = skill.lower()
                    skill_count[skill_lower] = skill_count.get(skill_lower, 0) + 1

        # Sort by frequency
        sorted_skills = sorted(skill_count.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_candidates_with_skills": len(candidates),
            "unique_skills": len(skill_count),
            "top_skills": [
                {"skill": skill, "count": count}
                for skill, count in sorted_skills[:20]
            ],
        }

    def get_experience_distribution(self, db: Session) -> dict:
        """Get experience level distribution."""
        candidates = db.query(Candidate).all()

        brackets = {
            "0-2 years": 0,
            "2-5 years": 0,
            "5-8 years": 0,
            "8-12 years": 0,
            "12+ years": 0,
        }

        for c in candidates:
            years = c.experience_years or 0
            if years <= 2:
                brackets["0-2 years"] += 1
            elif years <= 5:
                brackets["2-5 years"] += 1
            elif years <= 8:
                brackets["5-8 years"] += 1
            elif years <= 12:
                brackets["8-12 years"] += 1
            else:
                brackets["12+ years"] += 1

        return {
            "total_candidates": len(candidates),
            "distribution": brackets,
        }

    def get_hiring_funnel(self, db: Session, days: int = 30) -> dict:
        """Get hiring funnel metrics for the last N days."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        new_applications = db.query(JobApplication).filter(
            JobApplication.applied_at >= since
        ).count()

        interviews_conducted = db.query(Interview).filter(
            Interview.status == InterviewStatus.COMPLETED,
            Interview.completed_at >= since,
        ).count()

        evaluations = db.query(Evaluation).filter(
            Evaluation.evaluated_at >= since
        ).all()

        avg_score = 0
        if evaluations:
            avg_score = round(
                sum(e.overall_score for e in evaluations) / len(evaluations), 2
            )

        return {
            "period_days": days,
            "new_applications": new_applications,
            "interviews_conducted": interviews_conducted,
            "evaluations_completed": len(evaluations),
            "average_evaluation_score": avg_score,
        }


# Singleton
analytics_service = AnalyticsService()
