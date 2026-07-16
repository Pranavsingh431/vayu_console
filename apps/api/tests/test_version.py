"""Tests for GET /version."""

from __future__ import annotations

from httpx import AsyncClient


async def test_version_returns_build_identity(client: AsyncClient) -> None:
    response = await client.get("/version")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Vayu Console API"
    assert body["version"] == "0.1.0"
    assert body["environment"] == "development"


async def test_version_commit_is_null_when_not_deployed(client: AsyncClient) -> None:
    """GIT_COMMIT_SHA is injected by Render; locally it is simply unknown."""
    assert (await client.get("/version")).json()["commit"] is None
