"""Shared FastAPI dependencies.

Routes depend on the aliases here rather than importing concrete constructors,
so tests can override a single dependency instead of patching module globals.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.services.health_service import HealthService

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_health_service(settings: SettingsDep) -> HealthService:
    """Construct the health service for a request."""
    return HealthService(settings)


HealthServiceDep = Annotated[HealthService, Depends(get_health_service)]


#: A request-scoped database session. Routes depend on this rather than reaching
#: for the engine, so a test can override one seam.
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
