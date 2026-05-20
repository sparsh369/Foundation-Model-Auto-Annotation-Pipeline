"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-20

NOTE: For brevity this baseline uses a metadata-create approach. In a real deployment
generate this with `alembic revision --autogenerate` so up/down DDL is explicit and
reviewable. Kept here so `alembic upgrade head` produces the full schema out of the box.
"""
from __future__ import annotations

from alembic import op

from backend.app.db.base import Base
from backend.app import models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
