"""Idempotent seeding of the equipment catalog from versioned JSON.

The JSON files under ``app/data/exercise_library`` are the source of truth. Seeding is an upsert
keyed on ``equipment_id``. Rows removed from the file are deactivated, never deleted, because
``user_equipment`` rows (and later, exercise definitions and historic plans) reference them.
Library edits therefore never need a schema migration.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Union

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.services.exercise_library.equipment_aliases import (
    NEGATION_WORDS,
    NOOP_PHRASES,
    STOPWORDS,
    EquipmentAliasSource,
    find_alias_collisions,
    normalize_text,
)

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "exercise_library"
DEFAULT_EQUIPMENT_PATH = DATA_DIR / "equipment_v1.json"

_SLUG = r"^[a-z][a-z0-9_]*$"


class SeedValidationError(ValueError):
    def __init__(self, issues: List[str]) -> None:
        super().__init__("Invalid equipment seed file:\n- " + "\n- ".join(issues))
        self.issues = issues


class EquipmentSeedItem(BaseModel):
    equipment_id: str = Field(min_length=2, max_length=40, regex=_SLUG)
    name: str = Field(min_length=1, max_length=80)
    category: str = Field(min_length=1, max_length=30, regex=_SLUG)
    aliases: List[str] = Field(default_factory=list, max_items=30)


class EquipmentSeedFile(BaseModel):
    library_version: str = Field(min_length=1, max_length=20)
    equipment: List[EquipmentSeedItem] = Field(min_items=1)


@dataclass(frozen=True)
class SeedResult:
    created: int = 0
    updated: int = 0
    reactivated: int = 0
    deactivated: int = 0
    unchanged: int = 0

    @property
    def changed(self) -> bool:
        return bool(self.created or self.updated or self.reactivated or self.deactivated)


def load_equipment_seed(path: Union[str, Path] = DEFAULT_EQUIPMENT_PATH) -> EquipmentSeedFile:
    """Read and fully validate the seed file; raise SeedValidationError listing every problem."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SeedValidationError([f"cannot read {path}: {exc}"]) from exc

    try:
        parsed = EquipmentSeedFile.parse_obj(raw)
    except ValidationError as exc:
        raise SeedValidationError(
            [f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}" for err in exc.errors()]
        ) from exc

    issues: List[str] = []
    reserved = STOPWORDS | NEGATION_WORDS | NOOP_PHRASES

    seen_ids: Dict[str, int] = {}
    seen_names: Dict[str, str] = {}
    for item in parsed.equipment:
        seen_ids[item.equipment_id] = seen_ids.get(item.equipment_id, 0) + 1
        name_key = item.name.strip().lower()
        if name_key in seen_names:
            issues.append(f"duplicate name {item.name!r} ({seen_names[name_key]}, {item.equipment_id})")
        seen_names[name_key] = item.equipment_id

        for alias in item.aliases:
            normalized = normalize_text(alias)
            if not normalized:
                issues.append(f"{item.equipment_id}: alias {alias!r} is empty after normalization")
            elif normalized in reserved:
                issues.append(f"{item.equipment_id}: alias {alias!r} collides with a reserved word")

    issues.extend(f"duplicate equipment_id {eid!r}" for eid, count in seen_ids.items() if count > 1)

    collisions = find_alias_collisions(
        EquipmentAliasSource(item.equipment_id, item.name, item.aliases) for item in parsed.equipment
    )
    issues.extend(
        f"alias {phrase!r} is claimed by multiple items: {sorted(ids)}" for phrase, ids in sorted(collisions.items())
    )

    if issues:
        raise SeedValidationError(issues)
    return parsed


def seed_equipment(db: Session, path: Union[str, Path] = DEFAULT_EQUIPMENT_PATH) -> SeedResult:
    """Upsert the equipment catalog. Safe to run repeatedly (no-op when nothing changed)."""
    seed = load_equipment_seed(path)

    existing: Dict[str, Equipment] = {row.equipment_id: row for row in db.query(Equipment).all()}
    wanted_ids = {item.equipment_id for item in seed.equipment}

    created = updated = reactivated = deactivated = unchanged = 0

    for item in seed.equipment:
        row = existing.get(item.equipment_id)
        if row is None:
            db.add(
                Equipment(
                    equipment_id=item.equipment_id,
                    name=item.name,
                    category=item.category,
                    aliases=list(item.aliases),
                    is_active=True,
                )
            )
            created += 1
            continue

        was_inactive = not row.is_active
        fields_changed = (
            row.name != item.name or row.category != item.category or list(row.aliases or []) != item.aliases
        )
        if not (fields_changed or was_inactive):
            unchanged += 1
            continue

        row.name = item.name
        row.category = item.category
        row.aliases = list(item.aliases)
        row.is_active = True
        db.add(row)
        if was_inactive:
            reactivated += 1
        else:
            updated += 1

    for equipment_id, row in existing.items():
        if equipment_id not in wanted_ids and row.is_active:
            row.is_active = False
            db.add(row)
            deactivated += 1

    db.commit()

    result = SeedResult(
        created=created, updated=updated, reactivated=reactivated, deactivated=deactivated, unchanged=unchanged
    )
    logger.info(
        "exercise_library: equipment seed library_version=%s created=%s updated=%s reactivated=%s "
        "deactivated=%s unchanged=%s",
        seed.library_version,
        created,
        updated,
        reactivated,
        deactivated,
        unchanged,
    )
    return result
