"""Declarative base for ORM models.

No models exist yet (Phase 0 creates no application tables). Models added in
later phases must be imported in `app/models/__init__.py` so that Alembic's
autogenerate sees them on this metadata.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base. All ORM models inherit from this."""
