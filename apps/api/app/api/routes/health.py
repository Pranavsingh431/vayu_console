"""Health endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import HealthServiceDep
from app.schemas.health import HealthResponse

router = APIRouter(tags=["system"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service liveness and dependency status",
)
async def health(service: HealthServiceDep) -> HealthResponse:
    """Report service liveness and the status of each dependency.

    Always returns HTTP 200 while the process is alive. Inspect `status` to
    distinguish `ok` from `degraded`.
    """
    return await service.check()
