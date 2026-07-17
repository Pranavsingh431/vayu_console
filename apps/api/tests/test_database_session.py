"""Tests for engine configuration.

Regression: a full ingest died part-way with

    psycopg.errors.DuplicatePreparedStatement: prepared statement "_pg3_0" already exists

Supavisor's transaction mode (port 6543) multiplexes transactions across backends,
while psycopg3 prepares statements after the 5th execution and names them
predictably. The names then collide across backends.

An earlier stress test using a single statement shape passed 96/96 and wrongly
cleared this. These tests assert the wiring instead of trying to provoke the race:
a bug that only appears under sustained load cannot be pinned by a load test that
is too gentle to trigger it.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from app.core.config import Environment, Settings
from app.database import session as session_module


@pytest.fixture(autouse=True)
def _reset_engine() -> Iterator[None]:
    """The engine is a module-level singleton; isolate each test from it."""
    session_module._engine = None
    session_module._session_factory = None
    yield
    session_module._engine = None
    session_module._session_factory = None


def _settings(url: str) -> Settings:
    return Settings(environment=Environment.DEVELOPMENT, database_url=url, _env_file=None)


def test_prepared_statements_are_disabled_in_connect_args() -> None:
    """The driver must never implicitly prepare a statement."""
    assert session_module.CONNECT_ARGS["prepare_threshold"] is None


@pytest.mark.parametrize(
    "port",
    [
        6543,  # transaction mode — the mode that actually broke
        5432,  # session mode — must behave identically
    ],
)
def test_connect_args_reach_the_engine(port: int, monkeypatch: pytest.MonkeyPatch) -> None:
    """`CONNECT_ARGS` must actually be passed to the driver.

    Pinned for both ports so the app cannot break merely because DATABASE_URL was
    reconfigured from one pooler mode to the other.
    """
    captured: dict[str, Any] = {}

    def spy(dsn: str, **kwargs: Any) -> object:
        captured.update(kwargs)
        captured["dsn"] = dsn
        return object()

    monkeypatch.setattr(session_module, "create_async_engine", spy)
    session_module.get_engine(
        _settings(f"postgresql://u:p@aws-1-ap-south-1.pooler.supabase.com:{port}/postgres")
    )

    assert captured["connect_args"]["prepare_threshold"] is None, (
        "prepare_threshold must reach psycopg: Supavisor multiplexes transactions "
        "across backends and psycopg3's _pg3_N statement names collide."
    )
    assert captured["dsn"].startswith("postgresql+psycopg://")


def test_engine_is_cached() -> None:
    """One engine per process; a new one per call would leak connection pools."""
    settings = _settings("postgresql://u:p@host:5432/postgres")

    assert session_module.get_engine(settings) is session_module.get_engine(settings)
