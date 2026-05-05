"""Dialect-agnostic introspection for Alembic migrations (SQLite + PostgreSQL)."""

from __future__ import annotations

from typing import Set

from sqlalchemy import inspect
from sqlalchemy.engine import Connection


def table_column_names(connection: Connection, table_name: str) -> Set[str]:
    return {col["name"] for col in inspect(connection).get_columns(table_name)}
