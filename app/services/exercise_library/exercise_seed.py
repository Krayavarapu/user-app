"""Idempotent seeding of the exercise library from ``exercises_v1.json``.

Same contract as the equipment seed: the JSON file is the source of truth, seeding is an upsert
keyed on ``exercise_id``, exercises removed from the file are deactivated (never deleted, historic
plans reference them), and a library edit never needs a schema migration.

Validation is strict and reports every problem at once. A typo in a contraindication tag or an
unknown equipment id would otherwise silently weaken a safety filter, so a bad file aborts the
seed before the database is touched.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field, ValidationError, validator
from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.models.exercise import ExerciseDefinition, ExerciseEquipmentOption
from app.schemas.exercise import ImpactLevel, Laterality, Measure, Modality, MovementPattern
from app.services.exercise_library.seed import (
    DATA_DIR,
    SeedResult,
    SeedValidationError,
    seed_equipment,
)
from app.services.exercise_library.vocabulary import (
    CONTRAINDICATION_TAGS,
    EXERCISE_ID_PATTERN,
    GOAL_TAGS,
    MUSCLES,
    TEMPO_PATTERN,
)

logger = logging.getLogger(__name__)

DEFAULT_EXERCISES_PATH = DATA_DIR / "exercises_v1.json"


class ExerciseSource(BaseModel):
    kind: str = Field(min_length=1, max_length=30)
    ref: Optional[str] = Field(default=None, max_length=64)


class ExerciseSeedItem(BaseModel):
    exercise_id: str = Field(max_length=64)
    name: str = Field(min_length=1, max_length=120)
    movement_pattern: MovementPattern
    modality: Modality
    laterality: Laterality
    measure: Measure
    difficulty: int = Field(ge=1, le=3)
    primary_muscles: List[str] = Field(min_items=1)
    secondary_muscles: List[str] = Field(default_factory=list)
    equipment_options: List[List[str]] = Field(default_factory=list)
    contraindications: List[str] = Field(default_factory=list)
    goal_tags: List[str] = Field(min_items=1)
    impact_level: ImpactLevel
    default_tempo: Optional[str] = None
    source: ExerciseSource

    @validator("exercise_id")
    def _valid_id(cls, value: str) -> str:
        if not EXERCISE_ID_PATTERN.match(value):
            raise ValueError("must be lowercase letters, digits and underscores (3-64 chars)")
        return value

    @validator("default_tempo")
    def _valid_tempo(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not TEMPO_PATTERN.match(value):
            raise ValueError("must be four characters, each a digit or X (e.g. '3010')")
        return value


class ExerciseSeedFile(BaseModel):
    library_version: str = Field(min_length=1, max_length=20)
    exercises: List[ExerciseSeedItem] = Field(min_items=1)


def _vocabulary_issues(item: ExerciseSeedItem, equipment_ids: FrozenSet[str]) -> List[str]:
    issues: List[str] = []
    eid = item.exercise_id

    for field, values in (("primary_muscles", item.primary_muscles), ("secondary_muscles", item.secondary_muscles)):
        issues.extend(f"{eid}: unknown muscle {m!r} in {field}" for m in values if m not in MUSCLES)
        if len(set(values)) != len(values):
            issues.append(f"{eid}: duplicate entries in {field}")
    overlap = set(item.primary_muscles) & set(item.secondary_muscles)
    if overlap:
        issues.append(f"{eid}: muscles listed as both primary and secondary: {sorted(overlap)}")

    issues.extend(
        f"{eid}: unknown contraindication tag {t!r}" for t in item.contraindications if t not in CONTRAINDICATION_TAGS
    )
    issues.extend(f"{eid}: unknown goal tag {t!r}" for t in item.goal_tags if t not in GOAL_TAGS)
    if len(set(item.contraindications)) != len(item.contraindications):
        issues.append(f"{eid}: duplicate contraindication tags")

    seen_options: Set[Tuple[str, ...]] = set()
    for option in item.equipment_options:
        if not option:
            issues.append(f"{eid}: empty equipment option (use no options at all for bodyweight)")
            continue
        key = tuple(sorted(option))
        if len(set(option)) != len(option):
            issues.append(f"{eid}: equipment option repeats an item: {option}")
        if key in seen_options:
            issues.append(f"{eid}: duplicate equipment option {list(key)}")
        seen_options.add(key)
        issues.extend(f"{eid}: unknown equipment id {e!r}" for e in option if e not in equipment_ids)
    return issues


def load_exercise_seed(
    path: Union[str, Path] = DEFAULT_EXERCISES_PATH,
    *,
    equipment_ids: FrozenSet[str],
) -> ExerciseSeedFile:
    """Read and fully validate the exercise seed; raise SeedValidationError listing every problem."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SeedValidationError([f"cannot read {path}: {exc}"]) from exc

    try:
        parsed = ExerciseSeedFile.parse_obj(raw)
    except ValidationError as exc:
        raise SeedValidationError(
            [f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}" for err in exc.errors()]
        ) from exc

    issues: List[str] = []
    ids: Dict[str, int] = {}
    names: Dict[str, str] = {}
    for item in parsed.exercises:
        ids[item.exercise_id] = ids.get(item.exercise_id, 0) + 1
        key = item.name.strip().lower()
        if key in names:
            issues.append(f"duplicate name {item.name!r} ({names[key]}, {item.exercise_id})")
        names[key] = item.exercise_id
        issues.extend(_vocabulary_issues(item, equipment_ids))
    issues.extend(f"duplicate exercise_id {eid!r}" for eid, count in ids.items() if count > 1)

    if issues:
        raise SeedValidationError(issues)
    return parsed


def _normalized_options(options: List[List[str]]) -> List[List[str]]:
    return sorted(sorted(option) for option in options)


def _definition_fields(item: ExerciseSeedItem, library_version: str) -> Dict[str, Any]:
    return {
        "name": item.name,
        "movement_pattern": item.movement_pattern.value,
        "modality": item.modality.value,
        "laterality": item.laterality.value,
        "measure": item.measure.value,
        "difficulty": item.difficulty,
        "primary_muscles": list(item.primary_muscles),
        "secondary_muscles": list(item.secondary_muscles),
        "contraindications": sorted(item.contraindications),
        "goal_tags": sorted(item.goal_tags),
        "impact_level": item.impact_level.value,
        "default_tempo": item.default_tempo,
        "source_kind": item.source.kind,
        "source_ref": item.source.ref,
        "library_version": library_version,
    }


def seed_exercises(db: Session, path: Union[str, Path] = DEFAULT_EXERCISES_PATH) -> SeedResult:
    """Upsert the exercise library. Equipment must already be seeded (see ``seed_library``)."""
    equipment_ids = frozenset(
        row[0] for row in db.query(Equipment.equipment_id).filter(Equipment.is_active.is_(True)).all()
    )
    seed = load_exercise_seed(path, equipment_ids=equipment_ids)

    existing: Dict[str, ExerciseDefinition] = {row.exercise_id: row for row in db.query(ExerciseDefinition).all()}
    existing_options: Dict[str, Dict[int, List[str]]] = {}
    for row in db.query(ExerciseEquipmentOption).order_by(
        ExerciseEquipmentOption.exercise_id, ExerciseEquipmentOption.option_index
    ):
        existing_options.setdefault(row.exercise_id, {}).setdefault(row.option_index, []).append(row.equipment_id)

    wanted_ids = {item.exercise_id for item in seed.exercises}
    created = updated = reactivated = deactivated = unchanged = 0

    for item in seed.exercises:
        fields = _definition_fields(item, seed.library_version)
        desired_options = _normalized_options(item.equipment_options)
        row = existing.get(item.exercise_id)

        if row is None:
            db.add(ExerciseDefinition(exercise_id=item.exercise_id, is_active=True, **fields))
            _add_options(db, item.exercise_id, desired_options)
            created += 1
            continue

        current_options = _normalized_options(list(existing_options.get(item.exercise_id, {}).values()))
        was_inactive = not row.is_active
        fields_changed = any(getattr(row, key) != value for key, value in fields.items())
        options_changed = current_options != desired_options

        if not (fields_changed or options_changed or was_inactive):
            unchanged += 1
            continue

        for key, value in fields.items():
            setattr(row, key, value)
        row.is_active = True
        db.add(row)
        if options_changed:
            # Flush the deletion before re-inserting: the unit of work would otherwise insert
            # first and trip over the composite primary key.
            db.query(ExerciseEquipmentOption).filter(
                ExerciseEquipmentOption.exercise_id == item.exercise_id
            ).delete(synchronize_session=False)
            _add_options(db, item.exercise_id, desired_options)
        if was_inactive:
            reactivated += 1
        else:
            updated += 1

    for exercise_id, row in existing.items():
        if exercise_id not in wanted_ids and row.is_active:
            row.is_active = False
            db.add(row)
            deactivated += 1

    db.commit()

    result = SeedResult(
        created=created, updated=updated, reactivated=reactivated, deactivated=deactivated, unchanged=unchanged
    )
    logger.info(
        "exercise_library: exercise seed library_version=%s created=%s updated=%s reactivated=%s "
        "deactivated=%s unchanged=%s",
        seed.library_version,
        created,
        updated,
        reactivated,
        deactivated,
        unchanged,
    )
    return result


def _add_options(db: Session, exercise_id: str, options: List[List[str]]) -> None:
    for index, option in enumerate(options):
        for equipment_id in option:
            db.add(ExerciseEquipmentOption(exercise_id=exercise_id, option_index=index, equipment_id=equipment_id))


@dataclass(frozen=True)
class LibrarySeedResult:
    equipment: SeedResult
    exercises: SeedResult


def seed_library(db: Session) -> LibrarySeedResult:
    """Seed everything in the library: equipment first (exercises reference it), then exercises."""
    equipment_result = seed_equipment(db)
    exercise_result = seed_exercises(db)
    # Drop any cached library so this process picks up the new rows.
    from app.services.exercise_library.repository import clear_library_cache

    clear_library_cache()
    return LibrarySeedResult(equipment=equipment_result, exercises=exercise_result)
