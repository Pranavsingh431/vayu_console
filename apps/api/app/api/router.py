"""Root API router.

Aggregates every route module. Phase 0 exposes only the system endpoints;
versioned feature routers are mounted under `settings.api_v1_prefix` as they
are added.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import evidence, health, version

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(version.router)
api_router.include_router(evidence.router)
