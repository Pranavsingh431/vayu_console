"""Tests for GET /health."""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200


async def test_health_reports_ok_when_database_is_unconfigured(client: AsyncClient) -> None:
    """A fresh clone has no DATABASE_URL; that is reported, not treated as failure."""
    body = (await client.get("/health")).json()

    assert body["status"] == "ok"
    assert body["checks"]["database"]["status"] == "not_configured"


async def test_health_reports_environment_and_version(client: AsyncClient) -> None:
    body = (await client.get("/health")).json()

    assert body["environment"] == "development"
    assert body["version"] == "0.1.0"


async def test_health_response_carries_request_id(client: AsyncClient) -> None:
    """Every response is traceable back to a log line."""
    response = await client.get("/health")
    assert response.headers.get("X-Request-ID")
