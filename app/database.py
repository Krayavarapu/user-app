from __future__ import annotations

import logging
import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

_is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if _is_sqlite else {}
_engine_kwargs: dict = {}
if not _is_sqlite:
    _engine_kwargs["pool_pre_ping"] = True

engine = create_engine(DATABASE_URL, connect_args=connect_args, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

if _is_sqlite:
    _driver = "sqlite"
elif DATABASE_URL.lower().startswith("postgresql"):
    _driver = "postgresql"
else:
    _driver = "other"
logger.debug("database: engine ready driver_kind=%s", _driver)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
