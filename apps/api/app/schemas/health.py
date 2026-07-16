"""Response schemas for the health and version endpoints."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ComponentStatus(StrEnum):
    """Status of a single dependency."""

    OK = "ok"
    UNAVAILABLE = "unavailable"
    NOT_CONFIGURED = "not_configured"


class ServiceStatus(StrEnum):
    """Overall service status."""

    OK = "ok"
    DEGRADED = "degraded"


class ComponentHealth(BaseModel):
    """Health of one dependency, with timing when a probe actually ran."""

    model_config = ConfigDict(use_enum_values=True)

    status: ComponentStatus
    detail: str | None = Field(default=None, description="Human-readable context.")
    latency_ms: float | None = Field(default=None, description="Probe duration, if probed.")


class HealthResponse(BaseModel):
    """Response body for `GET /health`."""

    model_config = ConfigDict(use_enum_values=True)

    status: ServiceStatus
    environment: str
    version: str
    checks: dict[str, ComponentHealth]


class VersionResponse(BaseModel):
    """Response body for `GET /version`."""

    name: str
    version: str
    environment: str
    commit: str | None = Field(default=None, description="Deployed git SHA, if known.")
