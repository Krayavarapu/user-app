"""Read access to the exercise library, served from an immutable in-memory snapshot.

The library is small (hundreds of rows) and changes only when the seed runs at deploy time, so
the plan pipeline reads one cached snapshot instead of querying per request. Snapshots are frozen
dataclasses: callers cannot mutate shared state.

Cache lifetime: until ``clear_library_cache()`` (called by the seeder) or process restart. Render
seeds before starting the web process, so a new deploy always starts with a fresh cache.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import AbstractSet, Dict, FrozenSet, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.exercise import ExerciseDefinition, ExerciseEquipmentOption


@dataclass(frozen=True)
class ExerciseRecord:
    exercise_id: str
    name: str
    movement_pattern: str
    modality: str
    laterality: str
    measure: str
    difficulty: int
    primary_muscles: Tuple[str, ...]
    secondary_muscles: Tuple[str, ...]
    # OR of AND-sets. Empty tuple => no equipment needed (bodyweight).
    equipment_options: Tuple[FrozenSet[str], ...]
    contraindications: FrozenSet[str]
    goal_tags: FrozenSet[str]
    impact_level: str
    default_tempo: Optional[str]
    source_kind: str
    library_version: str

    @property
    def is_bodyweight(self) -> bool:
        return not self.equipment_options

    def is_available_with(self, owned_equipment: AbstractSet[str]) -> bool:
        """True if the exercise needs nothing, or any one option is fully covered by ``owned_equipment``."""
        return self.is_bodyweight or any(option <= owned_equipment for option in self.equipment_options)


@dataclass(frozen=True)
class ExerciseLibrary:
    exercises: Tuple[ExerciseRecord, ...]

    @property
    def by_id(self) -> Dict[str, ExerciseRecord]:
        return {record.exercise_id: record for record in self.exercises}

    def available_with(self, owned_equipment: Iterable[str]) -> List[ExerciseRecord]:
        owned = frozenset(owned_equipment)
        return [record for record in self.exercises if record.is_available_with(owned)]


_cache: Dict[str, ExerciseLibrary] = {}
_lock = threading.Lock()


def _cache_key(db: Session) -> str:
    return str(db.get_bind().url)


def clear_library_cache() -> None:
    with _lock:
        _cache.clear()


def load_library(db: Session) -> ExerciseLibrary:
    """Read the active library from the database (uncached)."""
    options: Dict[str, Dict[int, set]] = {}
    for row in db.query(ExerciseEquipmentOption).all():
        options.setdefault(row.exercise_id, {}).setdefault(row.option_index, set()).add(row.equipment_id)

    records = []
    definitions = (
        db.query(ExerciseDefinition)
        .filter(ExerciseDefinition.is_active.is_(True))
        .order_by(ExerciseDefinition.exercise_id)
        .all()
    )
    for row in definitions:
        exercise_options = options.get(row.exercise_id, {})
        records.append(
            ExerciseRecord(
                exercise_id=row.exercise_id,
                name=row.name,
                movement_pattern=row.movement_pattern,
                modality=row.modality,
                laterality=row.laterality,
                measure=row.measure,
                difficulty=row.difficulty,
                primary_muscles=tuple(row.primary_muscles or ()),
                secondary_muscles=tuple(row.secondary_muscles or ()),
                equipment_options=tuple(
                    frozenset(exercise_options[index]) for index in sorted(exercise_options)
                ),
                contraindications=frozenset(row.contraindications or ()),
                goal_tags=frozenset(row.goal_tags or ()),
                impact_level=row.impact_level,
                default_tempo=row.default_tempo,
                source_kind=row.source_kind,
                library_version=row.library_version,
            )
        )
    return ExerciseLibrary(exercises=tuple(records))


def get_library(db: Session) -> ExerciseLibrary:
    """Cached snapshot of the active library."""
    key = _cache_key(db)
    cached = _cache.get(key)
    if cached is not None:
        return cached
    library = load_library(db)
    with _lock:
        _cache[key] = library
    return library
