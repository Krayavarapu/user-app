from __future__ import annotations

import copy
import json
from collections import defaultdict

import pytest

from app.models.exercise import ExerciseDefinition, ExerciseEquipmentOption
from app.services.exercise_library.exercise_seed import (
    DEFAULT_EXERCISES_PATH,
    load_exercise_seed,
    seed_exercises,
    seed_library,
)
from app.services.exercise_library.repository import get_library
from app.services.exercise_library.seed import DEFAULT_EQUIPMENT_PATH, SeedValidationError, load_equipment_seed
from app.services.exercise_library.vocabulary import CONTRAINDICATION_TAGS, GOAL_TAGS, MUSCLES

EQUIPMENT_IDS = frozenset(item.equipment_id for item in load_equipment_seed(DEFAULT_EQUIPMENT_PATH).equipment)
ALL_EQUIPMENT = set(EQUIPMENT_IDS)


def shipped():
    return load_exercise_seed(DEFAULT_EXERCISES_PATH, equipment_ids=EQUIPMENT_IDS)


# --- the shipped library file -------------------------------------------------------------------


def test_shipped_library_is_valid_and_large_enough() -> None:
    seed = shipped()
    assert seed.library_version == "lib-v1"
    assert len(seed.exercises) >= 200


def test_every_vocabulary_value_is_controlled() -> None:
    for exercise in shipped().exercises:
        assert set(exercise.contraindications) <= CONTRAINDICATION_TAGS, exercise.exercise_id
        assert set(exercise.goal_tags) <= GOAL_TAGS, exercise.exercise_id
        assert set(exercise.primary_muscles + exercise.secondary_muscles) <= MUSCLES, exercise.exercise_id
        assert set(sum(exercise.equipment_options, [])) <= EQUIPMENT_IDS, exercise.exercise_id


def test_every_exercise_records_where_it_came_from() -> None:
    sources = {exercise.source.kind for exercise in shipped().exercises}
    assert sources == {"free-exercise-db", "in_house"}
    for exercise in shipped().exercises:
        if exercise.source.kind == "free-exercise-db":
            assert exercise.source.ref, exercise.exercise_id


def test_provenance_metadata_pins_the_source_commit() -> None:
    raw = json.loads(DEFAULT_EXERCISES_PATH.read_text())
    source = next(s for s in raw["sources"] if s["name"] == "free-exercise-db")
    assert len(source["commit"]) == 40
    assert "Unlicense" in source["license"]
    assert "images are not used" in source["used"].lower()


def test_no_exercise_text_is_copied_from_the_source() -> None:
    """Only facts are used; the source's instruction text and images must not appear."""
    forbidden = {"instructions", "images", "description"}
    for exercise in json.loads(DEFAULT_EXERCISES_PATH.read_text())["exercises"]:
        assert not forbidden & set(exercise), exercise["exercise_id"]


# --- Phase 2 acceptance: coverage ---------------------------------------------------------------
#
# Every movement pattern must offer at least 3 exercises for each equipment tier. A few
# combinations are genuinely impossible without padding the library with poor exercises; they are
# listed here explicitly so the gap is visible, and a second test fails when one gets fixed so
# the exception is removed.

TIERS = {
    "bodyweight": frozenset(),
    "dumbbell": frozenset({"dumbbell", "flat_bench", "adjustable_bench"}),
    "full_gym": frozenset(ALL_EQUIPMENT),
}
MIN_PER_CELL = 3

KNOWN_COVERAGE_GAPS = {
    ("carry", "bodyweight"),  # carrying needs something to carry
    ("vertical_pull", "bodyweight"),  # needs a bar, rings or a machine
    ("isolation_upper", "bodyweight"),  # curls, raises, extensions all need resistance
    ("vertical_push", "bodyweight"),  # only advanced pike / handstand push-ups
}


def coverage(records):
    patterns = sorted({r.movement_pattern for r in records})
    return {
        (pattern, tier): sum(1 for r in records if r.movement_pattern == pattern and r.is_available_with(owned))
        for pattern in patterns
        for tier, owned in TIERS.items()
    }


@pytest.fixture()
def library(db_session):
    seed_library(db_session)
    return get_library(db_session)


def test_every_pattern_has_enough_exercises_in_every_tier(library) -> None:
    short = {cell: n for cell, n in coverage(library.exercises).items() if n < MIN_PER_CELL}
    assert set(short) <= KNOWN_COVERAGE_GAPS, f"unexpected coverage gaps: {short}"


def test_documented_coverage_gaps_are_still_gaps(library) -> None:
    cells = coverage(library.exercises)
    fixed = {gap for gap in KNOWN_COVERAGE_GAPS if cells.get(gap, 0) >= MIN_PER_CELL}
    assert not fixed, f"these gaps are now covered; remove them from KNOWN_COVERAGE_GAPS: {fixed}"


def test_design_doc_minimum_menu_exists_for_a_bodyweight_user(library) -> None:
    """Doc section 8: 1+ of squat/lunge, hinge, push, pull, core, and 2+ warm-up items."""
    available = library.available_with([])
    patterns = {r.movement_pattern for r in available}
    assert patterns & {"squat", "lunge"}
    assert {"hinge", "horizontal_push"} <= patterns
    assert patterns & {"horizontal_pull", "vertical_pull"}  # prone raises give bodyweight pulling
    assert any(p.startswith("core_") for p in patterns)
    assert sum(1 for r in available if r.modality == "warmup") >= 2


def test_mobility_pool_supports_a_cool_down_and_a_warm_up(library) -> None:
    mobility = [r for r in library.exercises if r.movement_pattern == "mobility"]
    assert sum(1 for r in mobility if r.modality == "warmup") >= 10
    assert sum(1 for r in mobility if r.modality == "mobility") >= 10


def test_beginner_exercises_exist_in_every_tier(library) -> None:
    for tier, owned in TIERS.items():
        beginner = [r for r in library.exercises if r.difficulty == 1 and r.is_available_with(owned)]
        assert len(beginner) >= 20, tier


# --- loading validation -------------------------------------------------------------------------


def write_library(tmp_path, exercises, version="lib-test"):
    path = tmp_path / "exercises.json"
    path.write_text(json.dumps({"library_version": version, "exercises": exercises}), encoding="utf-8")
    return path


def exercise(exercise_id="goblet_squat", **overrides):
    base = {
        "exercise_id": exercise_id,
        "name": exercise_id.replace("_", " ").title(),
        "movement_pattern": "squat",
        "modality": "strength",
        "laterality": "bilateral",
        "measure": "reps",
        "difficulty": 1,
        "primary_muscles": ["quads"],
        "secondary_muscles": ["glutes"],
        "equipment_options": [["dumbbell"]],
        "contraindications": ["knee:deep_flexion_loaded"],
        "goal_tags": ["strength"],
        "impact_level": "low",
        "default_tempo": "3010",
        "source": {"kind": "in_house", "ref": None},
    }
    base.update(overrides)
    return base


def issues_for(tmp_path, *exercises):
    with pytest.raises(SeedValidationError) as info:
        load_exercise_seed(write_library(tmp_path, list(exercises)), equipment_ids=EQUIPMENT_IDS)
    return info.value.issues


@pytest.mark.parametrize(
    "overrides, fragment",
    [
        ({"contraindications": ["knee:high_impakt"]}, "unknown contraindication tag 'knee:high_impakt'"),
        ({"goal_tags": ["bulking"]}, "unknown goal tag 'bulking'"),
        ({"primary_muscles": ["quadriceps"]}, "unknown muscle 'quadriceps'"),
        ({"equipment_options": [["dumbell"]]}, "unknown equipment id 'dumbell'"),
        ({"equipment_options": [[]]}, "empty equipment option"),
        ({"equipment_options": [["dumbbell"], ["dumbbell"]]}, "duplicate equipment option"),
        ({"equipment_options": [["dumbbell", "dumbbell"]]}, "repeats an item"),
        ({"primary_muscles": ["quads"], "secondary_muscles": ["quads"]}, "both primary and secondary"),
        ({"contraindications": ["knee:high_impact", "knee:high_impact"]}, "duplicate contraindication"),
    ],
)
def test_bad_values_are_rejected(tmp_path, overrides, fragment) -> None:
    assert any(fragment in issue for issue in issues_for(tmp_path, exercise(**overrides))), fragment


@pytest.mark.parametrize(
    "overrides",
    [
        {"movement_pattern": "squatting"},
        {"modality": "cardio"},
        {"laterality": "both"},
        {"measure": "distance"},
        {"impact_level": "extreme"},
        {"difficulty": 0},
        {"difficulty": 4},
        {"default_tempo": "31"},
        {"default_tempo": "abcd"},
        {"exercise_id": "Goblet Squat"},
        {"exercise_id": "90_90_stretch"},
        {"primary_muscles": []},
        {"goal_tags": []},
    ],
)
def test_bad_fields_are_rejected(tmp_path, overrides) -> None:
    with pytest.raises(SeedValidationError):
        load_exercise_seed(write_library(tmp_path, [exercise(**overrides)]), equipment_ids=EQUIPMENT_IDS)


def test_duplicate_ids_and_names_are_reported_together(tmp_path) -> None:
    issues = issues_for(tmp_path, exercise("a_squat", name="Squat"), exercise("a_squat", name="squat"))
    assert any("duplicate exercise_id 'a_squat'" in i for i in issues)
    assert any("duplicate name" in i for i in issues)


def test_all_problems_are_reported_at_once(tmp_path) -> None:
    issues = issues_for(
        tmp_path,
        exercise("one", contraindications=["nope:nope"]),
        exercise("two", equipment_options=[["unobtainium"]], name="Two"),
    )
    assert len(issues) == 2


def test_unreadable_file_is_a_validation_error(tmp_path) -> None:
    with pytest.raises(SeedValidationError):
        load_exercise_seed(tmp_path / "missing.json", equipment_ids=EQUIPMENT_IDS)


# --- seeding behaviour --------------------------------------------------------------------------


def rows(db):
    return {r.exercise_id: r for r in db.query(ExerciseDefinition).all()}


def options(db, exercise_id):
    grouped = defaultdict(list)
    for row in db.query(ExerciseEquipmentOption).filter_by(exercise_id=exercise_id):
        grouped[row.option_index].append(row.equipment_id)
    return sorted(sorted(v) for v in grouped.values())


def test_seed_library_loads_equipment_then_exercises(db_session) -> None:
    result = seed_library(db_session)
    assert result.equipment.created >= 25
    assert result.exercises.created == len(shipped().exercises)
    assert db_session.query(ExerciseDefinition).count() == len(shipped().exercises)


def test_seeding_twice_changes_nothing(db_session) -> None:
    seed_library(db_session)
    before = {k: (v.name, v.contraindications, v.is_active) for k, v in rows(db_session).items()}
    option_rows = db_session.query(ExerciseEquipmentOption).count()

    again = seed_library(db_session)

    assert not again.exercises.changed and not again.equipment.changed
    assert again.exercises.unchanged == len(before)
    assert {k: (v.name, v.contraindications, v.is_active) for k, v in rows(db_session).items()} == before
    assert db_session.query(ExerciseEquipmentOption).count() == option_rows


def test_bodyweight_exercises_have_no_option_rows_and_alternatives_have_several(db_session) -> None:
    seed_library(db_session)
    assert options(db_session, "bodyweight_squat") == []
    assert options(db_session, "goblet_squat") == [["dumbbell"], ["kettlebell"]]
    assert options(db_session, "barbell_back_squat") == [["barbell", "squat_rack"]]


def test_removing_an_exercise_deactivates_it_instead_of_deleting(db_session, tmp_path) -> None:
    seed_library(db_session)
    raw = json.loads(DEFAULT_EXERCISES_PATH.read_text())
    raw["exercises"] = [e for e in raw["exercises"] if e["exercise_id"] != "goblet_squat"]
    path = tmp_path / "trimmed.json"
    path.write_text(json.dumps(raw))

    result = seed_exercises(db_session, path)

    assert result.deactivated == 1
    row = rows(db_session)["goblet_squat"]
    assert row.is_active is False
    assert options(db_session, "goblet_squat") == [["dumbbell"], ["kettlebell"]]  # history intact
    assert "goblet_squat" not in {r.exercise_id for r in get_library_fresh(db_session).exercises}


def get_library_fresh(db):
    from app.services.exercise_library.repository import clear_library_cache

    clear_library_cache()
    return get_library(db)


def test_restoring_a_removed_exercise_reactivates_it(db_session, tmp_path) -> None:
    seed_library(db_session)
    raw = json.loads(DEFAULT_EXERCISES_PATH.read_text())
    trimmed = copy.deepcopy(raw)
    trimmed["exercises"] = [e for e in raw["exercises"] if e["exercise_id"] != "goblet_squat"]
    path = tmp_path / "trimmed.json"
    path.write_text(json.dumps(trimmed))
    seed_exercises(db_session, path)

    result = seed_exercises(db_session, DEFAULT_EXERCISES_PATH)

    assert result.reactivated == 1
    assert rows(db_session)["goblet_squat"].is_active is True


def test_editing_fields_and_equipment_updates_in_place(db_session, tmp_path) -> None:
    seed_library(db_session)
    raw = json.loads(DEFAULT_EXERCISES_PATH.read_text())
    for entry in raw["exercises"]:
        if entry["exercise_id"] == "goblet_squat":
            entry["difficulty"] = 2
            entry["contraindications"] = sorted(entry["contraindications"] + ["spine:axial_loading_heavy"])
            entry["equipment_options"] = [["dumbbell"], ["kettlebell"], ["weight_plate"]]
    path = tmp_path / "edited.json"
    path.write_text(json.dumps(raw))

    result = seed_exercises(db_session, path)

    assert result.updated == 1 and result.created == 0
    row = rows(db_session)["goblet_squat"]
    assert row.difficulty == 2
    assert "spine:axial_loading_heavy" in row.contraindications
    assert options(db_session, "goblet_squat") == [["dumbbell"], ["kettlebell"], ["weight_plate"]]


def test_an_invalid_file_leaves_the_database_untouched(db_session, tmp_path) -> None:
    seed_library(db_session)
    raw = json.loads(DEFAULT_EXERCISES_PATH.read_text())
    raw["exercises"][0]["contraindications"] = ["typo:tag"]
    raw["exercises"][1]["name"] = "Changed But Never Applied"
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(raw))
    before_name = rows(db_session)[raw["exercises"][1]["exercise_id"]].name

    with pytest.raises(SeedValidationError):
        seed_exercises(db_session, path)

    db_session.expire_all()
    assert rows(db_session)[raw["exercises"][1]["exercise_id"]].name == before_name


def test_exercise_referencing_inactive_equipment_is_rejected(db_session) -> None:
    from app.models.equipment import Equipment

    seed_library(db_session)
    db_session.query(Equipment).filter_by(equipment_id="dumbbell").update({"is_active": False})
    db_session.commit()

    with pytest.raises(SeedValidationError) as info:
        seed_exercises(db_session)
    assert any("unknown equipment id 'dumbbell'" in i for i in info.value.issues)
