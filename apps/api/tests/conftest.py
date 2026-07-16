"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Environment, Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    """Settings for a test run, isolated from any developer `.env`."""
    return Settings(
        environment=Environment.DEVELOPMENT,
        app_version="0.1.0",
        log_format="console",
        database_url=None,
        cors_origins="http://localhost:3000",
        # Ignore any developer `.env`: tests must assert on fixed values, not on
        # whatever happens to be configured on the machine running them.
        _env_file=None,
    )


@pytest.fixture
def app(settings: Settings) -> Iterator[object]:
    """A FastAPI app built from test settings."""
    yield create_app(settings)


@pytest.fixture
async def client(app: object) -> AsyncIterator[AsyncClient]:
    """An HTTP client bound to the app, with no network involved."""
    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore[arg-type]
        base_url="http://test",
    ) as async_client:
        yield async_client
