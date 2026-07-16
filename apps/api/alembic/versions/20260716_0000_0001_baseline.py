"""baseline

Establishes the migration baseline for Vayu Console. Intentionally creates no
tables: Phase 0 only proves that the application, Alembic, and Supabase agree
on a connection. Applying this revision stamps `alembic_version` so that the
first real schema migration has a parent to revise.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-16
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
