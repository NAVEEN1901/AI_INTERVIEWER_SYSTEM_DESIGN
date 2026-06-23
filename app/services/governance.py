"""Governance & Security Service.

Provides:
- Prompt injection protection
- Cost monitoring
- Rate limiting tracking
- Audit logging
"""

import re
import time
from datetime import datetime, timezone
from collections import deque
from typing import Optional


class PromptGuard:
    """Detects and prevents prompt injection attacks."""

    INJECTION_PATTERNS = [
        r"ignore\s+(previous|above|all)\s+(instructions|prompts|rules)",
        r"disregard\s+(your|all|previous)\s+(instructions|rules|training)",
        r"you\s+are\s+now\s+(a|an|the)\s+",
        r"pretend\s+(you\s+are|to\s+be)",
        r"act\s+as\s+(if|though|a)",
        r"forget\s+(everything|all|your)\s+(above|previous)",
        r"system\s*:\s*",
        r"</?(system|user|assistant)>",
        r"\\n\s*(system|user|assistant)\s*:",
        r"jailbreak",
        r"DAN\s+mode",
    ]

    def __init__(self):
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS]

    def check_input(self, text: str) -> dict:
        """
        Check text for prompt injection attempts.
        
        Returns:
            dict with is_safe, confidence, detected_patterns
        """
        if not text:
            return {"is_safe": True, "confidence": 1.0, "detected_patterns": []}

        detected = []
        for pattern in self._compiled_patterns:
            if pattern.search(text):
                detected.append(pattern.pattern)

        is_safe = len(detected) == 0
        confidence = 1.0 - min(1.0, len(detected) * 0.3)

        return {
            "is_safe": is_safe,
            "confidence": round(confidence, 2),
            "detected_patterns": detected[:5],
        }

    def sanitize_input(self, text: str) -> str:
        """Remove potential injection patterns from input."""
        sanitized = text
        for pattern in self._compiled_patterns:
            sanitized = pattern.sub("[FILTERED]", sanitized)
        return sanitized


class CostMonitor:
    """Tracks API usage costs."""

    # Approximate costs per 1K tokens (USD)
    COST_PER_1K = {
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "whisper-1": {"per_minute": 0.006},
        "embeddings": {"input": 0.00002},
    }

    def __init__(self):
        self.usage_log: deque = deque(maxlen=10000)
        self.daily_totals: dict[str, float] = {}

    def record_usage(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        audio_minutes: float = 0,
    ):
        """Record API usage for cost tracking."""
        cost = self._calculate_cost(model, input_tokens, output_tokens, audio_minutes)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        self.usage_log.append({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "audio_minutes": audio_minutes,
            "cost_usd": cost,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        self.daily_totals[today] = self.daily_totals.get(today, 0) + cost

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int, audio_minutes: float) -> float:
        """Calculate cost for a usage record."""
        rates = self.COST_PER_1K.get(model, {"input": 0.001, "output": 0.002})

        if "per_minute" in rates:
            return audio_minutes * rates["per_minute"]

        cost = (input_tokens / 1000 * rates.get("input", 0) +
                output_tokens / 1000 * rates.get("output", 0))
        return round(cost, 6)

    def get_cost_summary(self, days: int = 30) -> dict:
        """Get cost summary for the last N days."""
        total_cost = sum(self.daily_totals.values())
        return {
            "total_cost_usd": round(total_cost, 4),
            "daily_breakdown": dict(sorted(self.daily_totals.items(), reverse=True)[:days]),
            "total_requests": len(self.usage_log),
        }


class AuditLogger:
    """Audit log for compliance and governance."""

    def __init__(self):
        self.logs: deque = deque(maxlen=10000)

    def log(self, user_id: int, action: str, resource: str, details: dict = None):
        """Record an audit event."""
        self.logs.append({
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_logs(self, user_id: Optional[int] = None, limit: int = 100) -> list[dict]:
        """Get audit logs, optionally filtered by user."""
        logs = list(self.logs)
        if user_id:
            logs = [l for l in logs if l["user_id"] == user_id]
        return logs[-limit:]


# Singletons
prompt_guard = PromptGuard()
cost_monitor = CostMonitor()
audit_logger = AuditLogger()
