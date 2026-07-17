"""Tests for configuration validation.

These cover the fail-fast contract: a production deploy missing required
configuration must not boot.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Environment, Settings


def test_production_requires_database_url() -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(environment=Environment.PRODUCTION, database_url=None, _env_file=None)


def test_production_rejects_debug_mode() -> None:
    with pytest.raises(ValidationError, match="DEBUG must be false"):
        Settings(
            environment=Environment.PRODUCTION,
            database_url="postgresql://u:p@host:5432/db",
            debug=True,
            _env_file=None,
        )


def test_development_allows_missing_database_url() -> None:
    """A fresh clone must run with no configuration at all."""
    settings = Settings(environment=Environment.DEVELOPMENT, database_url=None, _env_file=None)

    assert settings.database_dsn is None


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_optional_variables_are_treated_as_absent(blank: str) -> None:
    """`.env.example` ships blank values, and platforms allow empty vars.

    A blank DATABASE_URL must read as unconfigured rather than reaching the
    engine constructor as an empty string and failing there.
    """
    settings = Settings(database_url=blank, openrouter_api_key=blank, _env_file=None)

    assert settings.database_url is None
    assert settings.database_dsn is None
    assert settings.openrouter_api_key is None


def test_production_rejects_blank_database_url() -> None:
    """A blank required variable must fail as loudly as a missing one."""
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(environment=Environment.PRODUCTION, database_url="", _env_file=None)


@pytest.mark.parametrize(
    "given",
    [
        "postgresql://user:pass@db.supabase.co:5432/postgres",
        "postgres://user:pass@db.supabase.co:5432/postgres",
        "postgresql+asyncpg://user:pass@db.supabase.co:5432/postgres",
        "postgresql+psycopg://user:pass@db.supabase.co:5432/postgres",
    ],
)
def test_database_dsn_normalises_to_psycopg_driver(given: str) -> None:
    """Supabase hands out `postgresql://`; every variant must reach one driver."""
    settings = Settings(database_url=given, _env_file=None)

    assert settings.database_dsn == "postgresql+psycopg://user:pass@db.supabase.co:5432/postgres"


def test_database_dsn_preserves_query_parameters() -> None:
    """`sslmode` must survive normalisation — Supabase requires TLS."""
    settings = Settings(
        database_url="postgresql://u:p@db.supabase.co:5432/postgres?sslmode=require",
        _env_file=None,
    )

    assert settings.database_dsn is not None
    assert settings.database_dsn.endswith("?sslmode=require")


def test_cors_origins_parses_comma_separated_values() -> None:
    settings = Settings(
        cors_origins="http://localhost:3000, https://vayu.vercel.app ,",
        _env_file=None,
    )

    assert settings.cors_origin_list == ["http://localhost:3000", "https://vayu.vercel.app"]


def test_production_requires_cors_origins() -> None:
    """A blank CORS_ORIGINS blocks every browser while /health still returns 200.

    Regression: this shipped. The API answered curl in 600ms with
    `database: ok`, and the deployed console was blank, because the CORS
    middleware was never added. The failure must be loud at boot.
    """
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(
            environment=Environment.PRODUCTION,
            database_url="postgresql://u:p@host:5432/db",
            cors_origins="",
            _env_file=None,
        )


def test_production_boots_with_cors_origins_set() -> None:
    settings = Settings(
        environment=Environment.PRODUCTION,
        database_url="postgresql://u:p@host:5432/db",
        cors_origins="https://vayu-console.vercel.app",
        _env_file=None,
    )

    assert settings.cors_origin_list == ["https://vayu-console.vercel.app"]


def test_whitespace_only_cors_origins_is_rejected_in_production() -> None:
    """Whitespace parses to an empty list, which is the same silent failure."""
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(
            environment=Environment.PRODUCTION,
            database_url="postgresql://u:p@host:5432/db",
            cors_origins="  ,  ,",
            _env_file=None,
        )
