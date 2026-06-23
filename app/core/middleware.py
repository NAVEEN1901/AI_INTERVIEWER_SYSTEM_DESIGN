"""FastAPI middleware for monitoring and governance."""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.services.monitoring import metrics


class LatencyMiddleware(BaseHTTPMiddleware):
    """Tracks request latency for all endpoints."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        latency_ms = (time.time() - start_time) * 1000

        # Record metrics
        endpoint = f"{request.method} {request.url.path}"
        metrics.record_latency(endpoint, latency_ms, response.status_code)

        # Add latency header
        response.headers["X-Response-Time-Ms"] = f"{latency_ms:.2f}"
        return response
