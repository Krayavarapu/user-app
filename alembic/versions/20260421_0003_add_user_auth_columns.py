"""Add password_hash, holds, restrictions to users.

Revision ID: 20260421_0003
Revises: 20260420_0002
Create Date: 2026-04-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260421_0003"
down_revision = "20260420_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    columns = {row[1] for row in connection.execute(sa.text("PRAGMA table_info(users)"))}

    # Idempotent: skip if already applied (e.g. partial run or manual schema).
    if "password_hash" in columns and "holds" in columns and "restrictions" in columns:
        return

    # Placeholder for existing rows: not a valid salt$digest pair from app.security,
    # so verify_password returns False until the user is migrated or re-created via signup.
    legacy_password_placeholder = "__legacy_row_no_password__"

    op.add_column(
        "users",
        sa.Column(
            "password_hash",
            sa.String(length=255),
            nullable=False,
            server_default=legacy_password_placeholder,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "holds",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "restrictions",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    connection = op.get_bind()
    columns = {row[1] for row in connection.execute(sa.text("PRAGMA table_info(users)"))}

    if "restrictions" in columns:
        op.drop_column("users", "restrictions")
    if "holds" in columns:
        op.drop_column("users", "holds")
    if "password_hash" in columns:
        op.drop_column("users", "password_hash")
