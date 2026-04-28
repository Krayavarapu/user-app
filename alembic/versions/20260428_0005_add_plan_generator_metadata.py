"""Add provider metadata to fitness_plans.

Revision ID: 20260428_0005
Revises: 20260428_0004
Create Date: 2026-04-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260428_0005"
down_revision = "20260428_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    columns = {row[1] for row in connection.execute(sa.text("PRAGMA table_info(fitness_plans)"))}

    if "provider" not in columns:
        op.add_column(
            "fitness_plans",
            sa.Column("provider", sa.String(length=30), nullable=False, server_default="mock"),
        )
    if "generator_version" not in columns:
        op.add_column(
            "fitness_plans",
            sa.Column("generator_version", sa.String(length=40), nullable=False, server_default="mock-v1"),
        )


def downgrade() -> None:
    connection = op.get_bind()
    columns = {row[1] for row in connection.execute(sa.text("PRAGMA table_info(fitness_plans)"))}

    if "generator_version" in columns:
        op.drop_column("fitness_plans", "generator_version")
    if "provider" in columns:
        op.drop_column("fitness_plans", "provider")
