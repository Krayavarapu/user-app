from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Set

import pytest
from sqlalchemy import create_engine, inspect

from app.models.base import Base
from app.models.equipment import Equipment, UserEquipment
from app.models.exercise import ExerciseDefinition, ExerciseEquipmentOption
from app.models.user_profile import UserProfile

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_REVISION = "20260508_0006"
EQUIPMENT_REVISION = "20261007_0007"
LIBRARY_REVISION = "20261008_0008"
PROFILE_REVISION = "20261009_0009"  # head
EQUIPMENT_TABLES = {"equipment", "user_equipment"}
LIBRARY_TABLES = {"exercise_definitions", "exercise_equipment_options"}
PROFILE_TABLES = {"user_profiles"}
NEW_TABLES = EQUIPMENT_TABLES | LIBRARY_TABLES | PROFILE_TABLES


class MigrationDb:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.url = f"sqlite:///{path}"

    def alembic(self, *args: str) -> subprocess.CompletedProcess:
        # A subprocess keeps alembic's logging reconfiguration out of the test process.
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=ROOT,
            env={**os.environ, "DATABASE_URL": self.url},
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"alembic {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}"
        return result

    def tables(self) -> Set[str]:
        engine = create_engine(self.url)
        try:
            return set(inspect(engine).get_table_names())
        finally:
            engine.dispose()

    def indexes(self, table: str) -> Set[str]:
        engine = create_engine(self.url)
        try:
            return {index["name"] for index in inspect(engine).get_indexes(table)}
        finally:
            engine.dispose()

    def current(self) -> str:
        return self.alembic("current").stderr + self.alembic("current").stdout


@pytest.fixture()
def migration_db(tmp_path) -> MigrationDb:
    return MigrationDb(tmp_path / "migrations.db")


def test_upgrade_head_creates_equipment_library_and_profile_tables(migration_db) -> None:
    migration_db.alembic("upgrade", "head")

    assert NEW_TABLES <= migration_db.tables()
    assert "ix_user_equipment_user_id" in migration_db.indexes("user_equipment")
    assert "ix_exercise_definitions_movement_pattern" in migration_db.indexes("exercise_definitions")
    assert "ix_exercise_equipment_options_equipment_id" in migration_db.indexes("exercise_equipment_options")
    assert f"{PROFILE_REVISION} (head)" in migration_db.current()


def test_upgrade_head_twice_is_a_no_op(migration_db) -> None:
    migration_db.alembic("upgrade", "head")
    tables_after_first = migration_db.tables()
    migration_db.alembic("upgrade", "head")
    assert migration_db.tables() == tables_after_first


def test_downgrade_one_step_removes_only_the_profile_table(migration_db) -> None:
    migration_db.alembic("upgrade", "head")
    before = migration_db.tables()

    migration_db.alembic("downgrade", LIBRARY_REVISION)
    assert before - migration_db.tables() == PROFILE_TABLES
    assert EQUIPMENT_TABLES | LIBRARY_TABLES <= migration_db.tables()

    migration_db.alembic("upgrade", "head")
    assert migration_db.tables() == before


def test_downgrade_two_steps_removes_the_library_tables_too(migration_db) -> None:
    migration_db.alembic("upgrade", "head")
    before = migration_db.tables()

    migration_db.alembic("downgrade", EQUIPMENT_REVISION)
    assert before - migration_db.tables() == LIBRARY_TABLES | PROFILE_TABLES
    assert EQUIPMENT_TABLES <= migration_db.tables()

    migration_db.alembic("upgrade", "head")
    assert migration_db.tables() == before


def test_downgrade_removes_only_the_new_tables_and_can_reapply(migration_db) -> None:
    migration_db.alembic("upgrade", "head")
    before = migration_db.tables()

    migration_db.alembic("downgrade", PREVIOUS_REVISION)
    after = migration_db.tables()
    assert before - after == NEW_TABLES
    assert {"users", "user_sessions", "fitness_plans", "plan_days"} <= after

    migration_db.alembic("upgrade", "head")
    assert migration_db.tables() == before


def test_upgrade_tolerates_tables_that_already_exist(migration_db) -> None:
    """Render runs `alembic upgrade head` on every start, possibly on DBs created by create_all."""
    migration_db.alembic("upgrade", PREVIOUS_REVISION)

    engine = create_engine(migration_db.url)
    try:
        Base.metadata.create_all(bind=engine, tables=[Equipment.__table__, UserEquipment.__table__])
    finally:
        engine.dispose()
    assert {"equipment", "user_equipment"} <= migration_db.tables()

    migration_db.alembic("upgrade", "head")
    assert f"{PROFILE_REVISION} (head)" in migration_db.current()


def test_upgrade_tolerates_library_tables_that_already_exist(migration_db) -> None:
    migration_db.alembic("upgrade", EQUIPMENT_REVISION)

    engine = create_engine(migration_db.url)
    try:
        Base.metadata.create_all(
            bind=engine, tables=[ExerciseDefinition.__table__, ExerciseEquipmentOption.__table__]
        )
    finally:
        engine.dispose()

    migration_db.alembic("upgrade", "head")
    assert f"{PROFILE_REVISION} (head)" in migration_db.current()
    assert "ix_exercise_definitions_movement_pattern" in migration_db.indexes("exercise_definitions")


def test_upgrade_tolerates_profile_table_that_already_exists(migration_db) -> None:
    migration_db.alembic("upgrade", LIBRARY_REVISION)

    engine = create_engine(migration_db.url)
    try:
        Base.metadata.create_all(bind=engine, tables=[UserProfile.__table__])
    finally:
        engine.dispose()

    migration_db.alembic("upgrade", "head")
    assert f"{PROFILE_REVISION} (head)" in migration_db.current()


def test_profile_check_constraints_exist_in_the_migrated_table(migration_db) -> None:
    migration_db.alembic("upgrade", "head")
    engine = create_engine(migration_db.url)
    try:
        names = {c["name"] for c in inspect(engine).get_check_constraints("user_profiles")}
    finally:
        engine.dispose()
    assert {"ck_user_profiles_days_per_week", "ck_user_profiles_session_length"} <= names


def test_migrated_schema_matches_models(migration_db) -> None:
    """The migration and the SQLAlchemy models must describe the same columns and keys."""
    migration_db.alembic("upgrade", "head")
    engine = create_engine(migration_db.url)
    try:
        inspector = inspect(engine)
        for model in (Equipment, UserEquipment, ExerciseDefinition, ExerciseEquipmentOption, UserProfile):
            table = model.__table__
            migrated_columns = {col["name"]: col for col in inspector.get_columns(table.name)}
            assert set(migrated_columns) == {col.name for col in table.columns}, table.name
            for column in table.columns:
                assert migrated_columns[column.name]["nullable"] == column.nullable, (table.name, column.name)
            assert set(inspector.get_pk_constraint(table.name)["constrained_columns"]) == {
                col.name for col in table.primary_key.columns
            }
    finally:
        engine.dispose()
