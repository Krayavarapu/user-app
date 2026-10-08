"""Seed the exercise library reference data (equipment catalog and exercises).

    python -m app.scripts.seed_exercise_library

Idempotent: safe to run on every deploy. Requires the schema to be migrated first
(``alembic upgrade head``). Exits non-zero, before touching the database, if a seed file is invalid.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    # Load .env before importing app.database, which reads DATABASE_URL at import time.
    load_dotenv(_ROOT / ".env")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from app.database import SessionLocal
    from app.services.exercise_library.exercise_seed import seed_library
    from app.services.exercise_library.seed import SeedValidationError

    db = SessionLocal()
    try:
        result = seed_library(db)
    except SeedValidationError as exc:
        logging.getLogger(__name__).error("%s", exc)
        return 1
    finally:
        db.close()

    template = "{0}: created={1.created} updated={1.updated} reactivated={1.reactivated} " \
        "deactivated={1.deactivated} unchanged={1.unchanged}"
    print(template.format("equipment", result.equipment))
    print(template.format("exercises", result.exercises))
    return 0


if __name__ == "__main__":
    sys.exit(main())
