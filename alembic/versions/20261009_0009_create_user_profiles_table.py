"""Create user_profiles table.

Revision ID: 20261009_0009
Revises: 20261008_0008
Create Date: 2026-10-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20261009_0009"
down_revision = "20261008_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if inspect(op.get_bind()).has_table("user_profiles"):
        return

    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("experience_level", sa.String(length=20), nullable=False),
        sa.Column("primary_goal", sa.String(length=30), nullable=True),
        sa.Column("days_per_week", sa.Integer(), nullable=False),
        sa.Column("session_length_minutes", sa.Integer(), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("days_per_week BETWEEN 1 AND 7", name="ck_user_profiles_days_per_week"),
        sa.CheckConstraint("session_length_minutes BETWEEN 15 AND 120", name="ck_user_profiles_session_length"),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    if inspect(op.get_bind()).has_table("user_profiles"):
        op.drop_table("user_profiles")
