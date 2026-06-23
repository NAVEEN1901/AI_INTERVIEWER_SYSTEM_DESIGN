"""Monitoring & Observability Service.

Provides:
- Request latency tracking
- Model drift detection
- Health checks for all services
- Usage metrics
"""

import time
from datetime import datetime, timezone
from collections import deque
from typing import Optional

from app.core.config import settings


class MetricsCollector:
    """Collects and stores application metrics."""

    def __init__(self, max_history: int = 1000):
        self.request_latencies: deque = deque(maxlen=max_history)
        self.endpoint_counts: dict[str, int] = {}
        self.error_counts: dict[str, int] = {}
        self.model_predictions: deque = deque(maxlen=max_history)
        self.start_time = datetime.now(timezone.utc)

    def record_latency(self, endpoint: str, latency_ms: float, status_code: int):
        """Record a request latency."""
        self.request_latencies.append({
            "endpoint": endpoint,
            "latency_ms": latency_ms,
            "status_code": status_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.endpoint_counts[endpoint] = self.endpoint_counts.get(endpoint, 0) + 1
        if status_code >= 400:
            self.error_counts[endpoint] = self.error_counts.get(endpoint, 0) + 1

    def record_prediction(self, model_name: str, score: float, metadata: dict = None):
        """Record a model prediction for drift detection."""
        self.model_predictions.append({
            "model": model_name,
            "score": score,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_latency_stats(self) -> dict:
        """Get latency statistics."""
        if not self.request_latencies:
            return {"avg_ms": 0, "p50_ms": 0, "p95_ms": 0, "p99_ms": 0, "total_requests": 0}

        latencies = sorted(r["latency_ms"] for r in self.request_latencies)
        n = len(latencies)

        return {
            "avg_ms": round(sum(latencies) / n, 2),
            "p50_ms": round(latencies[n // 2], 2),
            "p95_ms": round(latencies[int(n * 0.95)], 2),
            "p99_ms": round(latencies[int(n * 0.99)], 2),
            "total_requests": n,
        }

    def get_endpoint_stats(self) -> dict:
        """Get per-endpoint request counts."""
        return {
            "endpoints": dict(sorted(self.endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:20]),
            "errors": self.error_counts,
        }

    def detect_drift(self, window_size: int = 100) -> dict:
        """
        Simple drift detection based on score distribution shift.
        Compares recent predictions to historical baseline.
        """
        predictions = list(self.model_predictions)
        if len(predictions) < window_size * 2:
            return {"status": "insufficient_data", "message": f"Need at least {window_size * 2} predictions"}

        # Split into baseline and recent
        baseline = [p["score"] for p in predictions[:-window_size]]
        recent = [p["score"] for p in predictions[-window_size:]]

        baseline_mean = sum(baseline) / len(baseline)
        recent_mean = sum(recent) / len(recent)
        drift_magnitude = abs(recent_mean - baseline_mean)

        # Simple threshold-based drift detection
        if drift_magnitude > 15:
            drift_status = "significant_drift"
        elif drift_magnitude > 5:
            drift_status = "minor_drift"
        else:
            drift_status = "no_drift"

        return {
            "status": drift_status,
            "baseline_mean": round(baseline_mean, 2),
            "recent_mean": round(recent_mean, 2),
            "drift_magnitude": round(drift_magnitude, 2),
            "window_size": window_size,
        }

    def get_uptime(self) -> dict:
        """Get application uptime."""
        now = datetime.now(timezone.utc)
        uptime = now - self.start_time
        return {
            "started_at": self.start_time.isoformat(),
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime_human": str(uptime).split(".")[0],
        }


class ServiceHealthChecker:
    """Checks health of all dependent services."""

    def check_database(self) -> dict:
        """Check PostgreSQL connectivity."""
        try:
            from app.db.session import engine
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            return {"status": "healthy", "service": "postgresql"}
        except Exception as e:
            return {"status": "unhealthy", "service": "postgresql", "error": str(e)}

    def check_vector_store(self) -> dict:
        """Check Qdrant connectivity."""
        try:
            from app.services.vector_store import vector_store
            info = vector_store.get_collection_info("resumes")
            return {"status": "healthy", "service": "qdrant", "info": info}
        except Exception as e:
            return {"status": "unhealthy", "service": "qdrant", "error": str(e)}

    def check_neo4j(self) -> dict:
        """Check Neo4j connectivity."""
        from app.services.knowledge_graph import knowledge_graph
        if knowledge_graph.is_available:
            return {"status": "healthy", "service": "neo4j"}
        return {"status": "unavailable", "service": "neo4j", "message": "Not configured"}

    def check_llm(self) -> dict:
        """Check LLM API availability."""
        from app.services.llm_service import llm_service
        if llm_service.is_available:
            return {"status": "healthy", "service": "llm", "model": llm_service.model}
        return {"status": "unavailable", "service": "llm", "message": "API key not configured"}

    def check_whisper(self) -> dict:
        """Check Whisper API availability."""
        from app.services.voice_service import whisper_service
        if whisper_service.is_available:
            return {"status": "healthy", "service": "whisper"}
        return {"status": "unavailable", "service": "whisper", "message": "API key not configured"}

    def check_all(self) -> dict:
        """Run all health checks."""
        checks = {
            "database": self.check_database(),
            "vector_store": self.check_vector_store(),
            "neo4j": self.check_neo4j(),
            "llm": self.check_llm(),
            "whisper": self.check_whisper(),
        }

        healthy_count = sum(1 for c in checks.values() if c["status"] == "healthy")
        total = len(checks)

        return {
            "overall": "healthy" if healthy_count >= 2 else "degraded",
            "healthy_services": healthy_count,
            "total_services": total,
            "services": checks,
        }


# Singletons
metrics = MetricsCollector()
health_checker = ServiceHealthChecker()
