"""Health inspection logic.

Kept out of the route layer so that probes can be reused (and unit-tested)
independently of HTTP.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy import text

from app.core.config import Settings
from app.database.session import get_engine
from app.schemas.health import ComponentHealth, ComponentStatus, HealthResponse, ServiceStatus

logger = logging.getLogger(__name__)

# A health probe must not hang a load balancer check behind a stalled socket.
_DB_PROBE_TIMEOUT_SECONDS = 5.0


class HealthService:
    """Probes the service's dependencies."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def check_database(self) -> ComponentHealth:
        """Probe database connectivity with a trivial round-trip."""
        if self._settings.database_dsn is None:
            return ComponentHealth(
                status=ComponentStatus.NOT_CONFIGURED,
                detail="DATABASE_URL is not set.",
            )

        start = time.perf_counter()
        try:
            engine = get_engine(self._settings)
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception as exc:
            logger.warning("database health probe failed", exc_info=exc)
            return ComponentHealth(
                status=ComponentStatus.UNAVAILABLE,
                detail=type(exc).__name__,
                latency_ms=round((time.perf_counter() - start) * 1000, 2),
            )

        return ComponentHealth(
            status=ComponentStatus.OK,
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
        )

    async def check(self) -> HealthResponse:
        """Build the full health report.

        An unavailable dependency reports `degraded` while the endpoint still
        returns HTTP 200: this is a liveness probe, and returning non-200 here
        would make Render recycle a process that is running correctly but whose
        database happens to be unreachable.
        """
        checks = {"database": await self.check_database()}

        degraded = any(check.status == ComponentStatus.UNAVAILABLE for check in checks.values())

        return HealthResponse(
            status=ServiceStatus.DEGRADED if degraded else ServiceStatus.OK,
            environment=str(self._settings.environment),
            version=self._settings.app_version,
            checks=checks,
        )
