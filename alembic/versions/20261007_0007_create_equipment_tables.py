"""Create equipment catalog and user_equipment tables.

Revision ID: 20261007_0007
Revises: 20260508_0006
Create Date: 2026-10-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20261007_0007"
down_revision = "20260508_0006"
branch_labels = None
depends_on = None

USER_EQUIPMENT_USER_INDEX = "ix_user_equipment_user_id"


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)

    if not inspector.has_table("equipment"):
        op.create_table(
            "equipment",
            sa.Column("equipment_id", sa.String(length=40), nullable=False),
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column("category", sa.String(length=30), nullable=False),
            sa.Column("aliases", sa.JSON(), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.PrimaryKeyConstraint("equipment_id"),
            sa.UniqueConstraint("name"),
        )

    if not inspector.has_table("user_equipment"):
        op.create_table(
            "user_equipment",
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("equipment_id", sa.String(length=40), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["equipment_id"], ["equipment.equipment_id"]),
            sa.PrimaryKeyConstraint("user_id", "equipment_id"),
        )

    existing_indexes = {index["name"] for index in inspect(connection).get_indexes("user_equipment")}
    if USER_EQUIPMENT_USER_INDEX not in existing_indexes:
        op.create_index(USER_EQUIPMENT_USER_INDEX, "user_equipment", ["user_id"], unique=False)


def downgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)

    if inspector.has_table("user_equipment"):
        existing_indexes = {index["name"] for index in inspector.get_indexes("user_equipment")}
        if USER_EQUIPMENT_USER_INDEX in existing_indexes:
            op.drop_index(USER_EQUIPMENT_USER_INDEX, table_name="user_equipment")
        op.drop_table("user_equipment")
    if inspector.has_table("equipment"):
        op.drop_table("equipment")
