"""Async SQLAlchemy engine and session management.

The engine is created lazily so that the application can boot — and answer
`/health` — without a database. That keeps a fresh clone runnable with no
configuration while still reporting the database as unconfigured.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when a database is required but DATABASE_URL is unset."""


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use."""
    global _engine

    if _engine is None:
        settings = settings or get_settings()
        dsn = settings.database_dsn
        if dsn is None:
            raise DatabaseNotConfiguredError(
                "DATABASE_URL is not set. Copy .env.example to .env and set it "
                "to your Supabase connection string."
            )
        _engine = create_async_engine(
            dsn,
            echo=settings.db_echo,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            # Supabase closes idle connections; recycle below that window so a
            # pooled connection is never handed out already dead.
            pool_recycle=1800,
            pool_pre_ping=True,
        )
        logger.info("database engine created")

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory, creating it on first use."""
    global _session_factory

    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    return _session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped session.

    Unused in Phase 0 (no endpoint touches the database) but defined here so
    that routes added later inject a session rather than reaching for a global.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Close all pooled connections. Called on application shutdown."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("database engine disposed")
