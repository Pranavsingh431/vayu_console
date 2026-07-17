"""Typed application configuration.

Settings are read from the process environment first, then from a ``.env`` file
at the repository root (local development only). On Render and Vercel the values
come from the platform's environment variable store and no ``.env`` file exists.

Validation is intentionally asymmetric:

* In ``production`` every operationally required variable must be present, and
  the process refuses to start otherwise — a misconfigured deploy should fail
  loudly at boot rather than serve wrong answers at 3am.
* In ``development`` the same variables are optional so that a fresh clone can
  run ``/health`` with no setup. ``/health`` reports what is unconfigured.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AliasChoices, BeforeValidator, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/api/app/core/config.py -> parents[4] is the repository root.
REPO_ROOT = Path(__file__).resolve().parents[4]
API_ROOT = Path(__file__).resolve().parents[2]


def _blank_to_none(value: object) -> object:
    """Treat a blank environment variable as absent.

    `.env.example` ships keys with empty values, and both Render and Vercel let
    you declare a variable with no value. Without this, `DATABASE_URL=` reads as
    the string `""` — which is truthy enough to reach the engine constructor and
    fail there, instead of being reported as simply unconfigured.
    """
    if isinstance(value, str) and not value.strip():
        return None
    return value


# Optional settings: blank and absent mean the same thing.
OptionalStr = Annotated[str | None, BeforeValidator(_blank_to_none)]


class Environment(StrEnum):
    """Deployment environment the process believes it is running in."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings, validated once at import time."""

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", API_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -- Application ------------------------------------------------------
    app_name: str = "Vayu Console API"
    app_version: str = "0.1.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Render injects RENDER_GIT_COMMIT into every deploy, so /version reports the
    # live commit with no extra configuration. GIT_COMMIT_SHA overrides it.
    git_commit_sha: OptionalStr = Field(
        default=None,
        validation_alias=AliasChoices("GIT_COMMIT_SHA", "RENDER_GIT_COMMIT"),
    )

    # -- Logging ----------------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"

    # -- CORS -------------------------------------------------------------
    # Comma-separated so it round-trips cleanly through platform env vars,
    # which have no way to express a JSON list.
    cors_origins: str = "http://localhost:3000"

    # -- Database ---------------------------------------------------------
    # Supabase hands out a `postgresql://` URL; normalised to the psycopg3
    # driver in `database_dsn` so the same value works for app and Alembic.
    database_url: OptionalStr = None
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_echo: bool = False

    # -- Cache ------------------------------------------------------------
    # Reserved: Redis is part of the architecture but not connected in Phase 0.
    redis_url: OptionalStr = None

    # -- External data sources --------------------------------------------
    # All optional: no feature consumes them yet. Each phase that starts using
    # one is responsible for promoting it to required in `_validate_for_environment`.
    openrouter_api_key: OptionalStr = None
    data_gov_api_key: OptionalStr = None
    # Discovery of locations/sensors only. Its measurements endpoint returns empty
    # for history that exists; historical readings come from the keyless S3 archive.
    openaq_api_key: OptionalStr = None
    nasa_firms_api_key: OptionalStr = None
    nasa_earthdata_bearer_token: OptionalStr = None
    copernicus_username: OptionalStr = None
    copernicus_password: OptionalStr = None

    # -- Supabase ---------------------------------------------------------
    supabase_url: OptionalStr = None
    supabase_anon_key: OptionalStr = None
    supabase_service_role_key: OptionalStr = None

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a list, ignoring blanks and stray whitespace."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION

    @property
    def database_dsn(self) -> str | None:
        """`database_url` normalised to the async psycopg3 driver.

        psycopg3 is used rather than asyncpg because it accepts libpq-style
        query parameters (notably `sslmode=require`, which Supabase includes in
        its connection strings) and drives both the app and Alembic.
        """
        if self.database_url is None:
            return None
        url = self.database_url
        for prefix in (
            "postgresql+psycopg://",
            "postgresql+asyncpg://",
            "postgresql://",
            "postgres://",
        ):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix) :]
        return url

    @model_validator(mode="after")
    def _validate_for_environment(self) -> Settings:
        """Fail fast when a deployed environment is missing what it needs."""
        if not self.is_production:
            return self

        missing = [name for name in ("database_url",) if getattr(self, name) is None]
        if missing:
            raise ValueError(
                "Missing required environment variables for production: "
                + ", ".join(sorted(name.upper() for name in missing))
                + ". Set them in the Render dashboard (see docs/deployment.md)."
            )
        if self.debug:
            raise ValueError("DEBUG must be false in production.")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton.

    Cached so that validation runs once and every caller observes identical
    configuration. Tests clear the cache via `get_settings.cache_clear()`.
    """
    return Settings()
