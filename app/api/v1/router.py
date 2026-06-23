"""API v1 router - aggregates all endpoint routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, users, jobs, resumes, search,
    notifications, analytics, interviews, voice, graph, ops,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(jobs.router)
api_router.include_router(resumes.router)
api_router.include_router(search.router)
api_router.include_router(notifications.router)
api_router.include_router(analytics.router)
api_router.include_router(interviews.router)
api_router.include_router(voice.router)
api_router.include_router(graph.router)
api_router.include_router(ops.router)
