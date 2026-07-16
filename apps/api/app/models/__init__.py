"""SQLAlchemy ORM models.

Phase 0 defines no application tables. Every model added later must be imported
here so that `Base.metadata` is fully populated when Alembic autogenerates a
migration — a model that is never imported is silently invisible to autogenerate.
"""

from app.database.base import Base

__all__ = ["Base"]
