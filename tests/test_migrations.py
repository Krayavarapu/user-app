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

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_REVISION = "20260508_0006"
EQUIPMENT_REVISION = "20261007_0007"


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


def test_upgrade_head_creates_equipment_tables(migration_db) -> None:
    migration_db.alembic("upgrade", "head")

    assert {"equipment", "user_equipment"} <= migration_db.tables()
    assert "ix_user_equipment_user_id" in migration_db.indexes("user_equipment")
    assert f"{EQUIPMENT_REVISION} (head)" in migration_db.current()


def test_upgrade_head_twice_is_a_no_op(migration_db) -> None:
    migration_db.alembic("upgrade", "head")
    tables_after_first = migration_db.tables()
    migration_db.alembic("upgrade", "head")
    assert migration_db.tables() == tables_after_first


def test_downgrade_removes_only_the_equipment_tables_and_can_reapply(migration_db) -> None:
    migration_db.alembic("upgrade", "head")
    before = migration_db.tables()

    migration_db.alembic("downgrade", PREVIOUS_REVISION)
    after = migration_db.tables()
    assert before - after == {"equipment", "user_equipment"}
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
    assert f"{EQUIPMENT_REVISION} (head)" in migration_db.current()


def test_migrated_schema_matches_models(migration_db) -> None:
    """The migration and the SQLAlchemy models must describe the same columns and keys."""
    migration_db.alembic("upgrade", "head")
    engine = create_engine(migration_db.url)
    try:
        inspector = inspect(engine)
        for model in (Equipment, UserEquipment):
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
