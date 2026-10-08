"""Seed the exercise library reference data.

    python -m app.scripts.seed_exercise_library

Idempotent: safe to run on every deploy. Requires the schema to be migrated first
(``alembic upgrade head``). Currently seeds the equipment catalog; exercises are added later.
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
    from app.services.exercise_library.seed import SeedValidationError, seed_equipment

    db = SessionLocal()
    try:
        result = seed_equipment(db)
    except SeedValidationError as exc:
        logging.getLogger(__name__).error("%s", exc)
        return 1
    finally:
        db.close()

    print(
        "equipment: created={0.created} updated={0.updated} reactivated={0.reactivated} "
        "deactivated={0.deactivated} unchanged={0.unchanged}".format(result)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
