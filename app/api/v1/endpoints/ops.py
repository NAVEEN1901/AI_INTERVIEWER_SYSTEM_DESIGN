"""Monitoring, Governance & Operations endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from app.core.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.services.monitoring import metrics, health_checker
from app.services.governance import prompt_guard, cost_monitor, audit_logger

router = APIRouter(prefix="/ops", tags=["Operations & Monitoring"])


# --- Schemas ---

class PromptCheckRequest(BaseModel):
    text: str


# --- Health & Monitoring ---

@router.get("/health")
def detailed_health_check(
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    """Comprehensive health check of all services."""
    return health_checker.check_all()


@router.get("/metrics")
def get_metrics(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Get application metrics (latency, requests, errors)."""
    return {
        "latency": metrics.get_latency_stats(),
        "endpoints": metrics.get_endpoint_stats(),
        "uptime": metrics.get_uptime(),
    }


@router.get("/drift")
def check_model_drift(
    window_size: int = 100,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Check for model prediction drift."""
    return metrics.detect_drift(window_size=window_size)


# --- Governance & Security ---

@router.post("/check-prompt")
def check_prompt_injection(
    payload: PromptCheckRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.HR)),
):
    """
    Check text for prompt injection attempts.
    Use before sending user input to LLM.
    """
    result = prompt_guard.check_input(payload.text)
    return {
        **result,
        "sanitized_text": prompt_guard.sanitize_input(payload.text) if not result["is_safe"] else payload.text,
    }


@router.get("/costs")
def get_cost_summary(
    days: int = 30,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Get API usage cost summary."""
    return cost_monitor.get_cost_summary(days=days)


@router.get("/audit-logs")
def get_audit_logs(
    user_id: Optional[int] = None,
    limit: int = 100,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Get audit logs for governance compliance."""
    return {
        "logs": audit_logger.get_logs(user_id=user_id, limit=limit),
        "total": len(audit_logger.logs),
    }
