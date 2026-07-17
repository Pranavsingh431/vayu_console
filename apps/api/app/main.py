"""Vayu Console API — application entrypoint.

Run locally:
    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.core.middleware import RequestLoggingMiddleware
from app.database.session import dispose_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage resources bound to the application's lifetime."""
    settings: Settings = app.state.settings
    logger.info(
        "starting %s",
        settings.app_name,
        extra={"environment": str(settings.environment), "version": settings.app_version},
    )
    try:
        yield
    finally:
        await dispose_engine()
        logger.info("shutdown complete")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application.

    A factory rather than a module-level singleton so tests can construct an
    app with alternate settings without mutating global state.

    When `settings` is supplied it is bound to the `get_settings` dependency, so
    that routes resolve the settings given here rather than the process-wide
    cached ones. Without that binding the argument would be silently ignored by
    every route — and a test asking for "no database" would quietly talk to the
    real one.
    """
    explicit_settings = settings is not None
    settings = settings or get_settings()
    configure_logging(level=settings.log_level, log_format=settings.log_format)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        summary="Urban air quality decision intelligence for municipal officers.",
        lifespan=lifespan,
        # Interactive docs are useful in development and a needless surface in
        # production, where this API is consumed by the web app.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.state.settings = settings

    if explicit_settings:
        # Bind the caller's settings to the dependency the routes actually
        # resolve. `app.state` alone is not enough: nothing reads it per-request.
        app.dependency_overrides[get_settings] = lambda: settings

    app.add_middleware(RequestLoggingMiddleware)

    if not settings.cors_origin_list:
        # Production refuses to boot in this state (see config validation); in
        # development, say so rather than leaving a developer to debug a blank
        # page against an API that answers curl perfectly.
        logger.warning(
            "CORS_ORIGINS is empty — every browser request will be blocked while "
            "curl still succeeds. Set CORS_ORIGINS to your web origin.",
        )
    else:
        from fastapi.middleware.cors import CORSMiddleware

        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID"],
        )

    app.include_router(api_router)
    return app


app = create_app()
