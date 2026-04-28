"""Create fitness_plans and plan_days tables.

Revision ID: 20260428_0004
Revises: 20260421_0003
Create Date: 2026-04-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260428_0004"
down_revision = "20260421_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not inspector.has_table("fitness_plans"):
        op.create_table(
            "fitness_plans",
            sa.Column("plan_id", sa.String(length=64), primary_key=True),
            sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.user_id"), nullable=False),
            sa.Column("title", sa.String(length=150), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("goal", sa.String(length=120), nullable=False),
            sa.Column("equipment", sa.String(length=300), nullable=False),
            sa.Column("duration_days", sa.Integer(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_fitness_plans_plan_id", "fitness_plans", ["plan_id"], unique=False)
        op.create_index("ix_fitness_plans_user_id", "fitness_plans", ["user_id"], unique=False)

    inspector = sa.inspect(connection)
    if not inspector.has_table("plan_days"):
        op.create_table(
            "plan_days",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("plan_id", sa.String(length=64), sa.ForeignKey("fitness_plans.plan_id"), nullable=False),
            sa.Column("day_number", sa.Integer(), nullable=False),
            sa.Column("day_label", sa.String(length=40), nullable=False),
            sa.Column("focus", sa.String(length=80), nullable=False),
            sa.Column("workout_json", sa.Text(), nullable=False),
            sa.UniqueConstraint("plan_id", "day_number", name="uq_plan_days_plan_day_number"),
        )
        op.create_index("ix_plan_days_plan_id", "plan_days", ["plan_id"], unique=False)


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if inspector.has_table("plan_days"):
        op.drop_index("ix_plan_days_plan_id", table_name="plan_days")
        op.drop_table("plan_days")

    inspector = sa.inspect(connection)
    if inspector.has_table("fitness_plans"):
        op.drop_index("ix_fitness_plans_user_id", table_name="fitness_plans")
        op.drop_index("ix_fitness_plans_plan_id", table_name="fitness_plans")
        op.drop_table("fitness_plans")
