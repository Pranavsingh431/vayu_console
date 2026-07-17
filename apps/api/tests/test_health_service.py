"""Tests for the database health probe.

These pin two behaviours that a production incident exposed: an unreachable
database must not hang the probe, and must not emit a full traceback on every
poll (Render probes /health every few seconds, which buried the logs).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import pytest

from app.core.config import Environment, Settings
from app.schemas.health import ComponentStatus
from app.services import health_service
from app.services.health_service import HealthService, _root_cause


@pytest.fixture
def configured_settings() -> Settings:
    return Settings(
        environment=Environment.DEVELOPMENT,
        database_url="postgresql://u:p@db.example.com:5432/postgres",
        _env_file=None,
    )


def test_root_cause_unwraps_to_the_innermost_message() -> None:
    """SQLAlchemy buries the real reason several `raise ... from` layers down."""
    inner = OSError("Network is unreachable")
    middle = RuntimeError("connect failed")
    middle.__cause__ = inner
    outer = RuntimeError("engine error")
    outer.__cause__ = middle

    assert _root_cause(outer) == "Network is unreachable"


def test_root_cause_keeps_only_the_first_line() -> None:
    exc = OSError("first line\nsecond line\nthird line")

    assert _root_cause(exc) == "first line"


async def test_unreachable_database_reports_unavailable(
    configured_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(_settings: Any) -> Any:
        raise OSError("Network is unreachable")

    monkeypatch.setattr(health_service, "get_engine", boom)

    result = await HealthService(configured_settings).check_database()

    assert result.status == ComponentStatus.UNAVAILABLE
    assert result.detail == "OSError"


async def test_unreachable_database_logs_one_line_without_a_traceback(
    configured_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A traceback per probe floods the log; the cause alone is what's useful."""

    def boom(_settings: Any) -> Any:
        raise OSError("Network is unreachable")

    monkeypatch.setattr(health_service, "get_engine", boom)

    with caplog.at_level(logging.WARNING, logger=health_service.__name__):
        await HealthService(configured_settings).check_database()

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert warnings[0].exc_info is None, "traceback must not be attached at WARNING"
    # `cause` is attached via `extra=`, so it lives in __dict__ rather than
    # being a declared LogRecord attribute.
    assert warnings[0].__dict__["cause"] == "Network is unreachable"


async def test_slow_database_probe_times_out(
    configured_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stalled socket must not hold /health open indefinitely.

    `engine.connect()` returns an async context manager, so a hang shows up as
    an `__aenter__` that never resolves — a TCP connect to a black-holed host.
    """

    class StalledConnection:
        async def __aenter__(self) -> Any:
            await asyncio.sleep(60)
            raise AssertionError("should have timed out")

        async def __aexit__(self, *_exc: Any) -> None:
            return None

    class StalledEngine:
        def connect(self) -> StalledConnection:
            return StalledConnection()

    monkeypatch.setattr(health_service, "_DB_PROBE_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(health_service, "get_engine", lambda _s: StalledEngine())

    result = await asyncio.wait_for(
        HealthService(configured_settings).check_database(),
        timeout=5,
    )

    assert result.status == ComponentStatus.UNAVAILABLE
    assert "exceeded" in (result.detail or "")
