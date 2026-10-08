"""Create exercise_definitions and exercise_equipment_options tables.

Revision ID: 20261008_0008
Revises: 20261007_0007
Create Date: 2026-10-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20261008_0008"
down_revision = "20261007_0007"
branch_labels = None
depends_on = None

PATTERN_INDEX = "ix_exercise_definitions_movement_pattern"
OPTION_EQUIPMENT_INDEX = "ix_exercise_equipment_options_equipment_id"


def _index_names(connection, table: str) -> set:
    return {index["name"] for index in inspect(connection).get_indexes(table)}


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)

    if not inspector.has_table("exercise_definitions"):
        op.create_table(
            "exercise_definitions",
            sa.Column("exercise_id", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("movement_pattern", sa.String(length=30), nullable=False),
            sa.Column("modality", sa.String(length=20), nullable=False),
            sa.Column("laterality", sa.String(length=20), nullable=False),
            sa.Column("measure", sa.String(length=10), nullable=False),
            sa.Column("difficulty", sa.Integer(), nullable=False),
            sa.Column("primary_muscles", sa.JSON(), nullable=False),
            sa.Column("secondary_muscles", sa.JSON(), nullable=False),
            sa.Column("contraindications", sa.JSON(), nullable=False),
            sa.Column("goal_tags", sa.JSON(), nullable=False),
            sa.Column("impact_level", sa.String(length=10), nullable=False),
            sa.Column("default_tempo", sa.String(length=4), nullable=True),
            sa.Column("source_kind", sa.String(length=30), nullable=False),
            sa.Column("source_ref", sa.String(length=64), nullable=True),
            sa.Column("library_version", sa.String(length=20), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.PrimaryKeyConstraint("exercise_id"),
        )

    if PATTERN_INDEX not in _index_names(connection, "exercise_definitions"):
        op.create_index(PATTERN_INDEX, "exercise_definitions", ["movement_pattern"], unique=False)

    if not inspect(connection).has_table("exercise_equipment_options"):
        op.create_table(
            "exercise_equipment_options",
            sa.Column("exercise_id", sa.String(length=64), nullable=False),
            sa.Column("option_index", sa.Integer(), nullable=False),
            sa.Column("equipment_id", sa.String(length=40), nullable=False),
            sa.ForeignKeyConstraint(
                ["exercise_id"], ["exercise_definitions.exercise_id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["equipment_id"], ["equipment.equipment_id"]),
            sa.PrimaryKeyConstraint("exercise_id", "option_index", "equipment_id"),
        )

    if OPTION_EQUIPMENT_INDEX not in _index_names(connection, "exercise_equipment_options"):
        op.create_index(
            OPTION_EQUIPMENT_INDEX, "exercise_equipment_options", ["equipment_id"], unique=False
        )


def downgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)

    if inspector.has_table("exercise_equipment_options"):
        if OPTION_EQUIPMENT_INDEX in _index_names(connection, "exercise_equipment_options"):
            op.drop_index(OPTION_EQUIPMENT_INDEX, table_name="exercise_equipment_options")
        op.drop_table("exercise_equipment_options")

    if inspect(connection).has_table("exercise_definitions"):
        if PATTERN_INDEX in _index_names(connection, "exercise_definitions"):
            op.drop_index(PATTERN_INDEX, table_name="exercise_definitions")
        op.drop_table("exercise_definitions")
