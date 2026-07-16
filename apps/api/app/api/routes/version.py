"""Version endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import SettingsDep
from app.schemas.health import VersionResponse

router = APIRouter(tags=["system"])


@router.get(
    "/version",
    response_model=VersionResponse,
    summary="Build and deployment identity",
)
async def version(settings: SettingsDep) -> VersionResponse:
    """Report which build is running, so a deploy can be confirmed."""
    return VersionResponse(
        name=settings.app_name,
        version=settings.app_version,
        environment=str(settings.environment),
        commit=settings.git_commit_sha,
    )
