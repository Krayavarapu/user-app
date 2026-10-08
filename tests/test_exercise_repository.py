from __future__ import annotations

from app.models.exercise import ExerciseDefinition
from app.services.exercise_library.exercise_seed import seed_library
from app.services.exercise_library.repository import (
    ExerciseRecord,
    clear_library_cache,
    get_library,
    load_library,
)


def record(**overrides) -> ExerciseRecord:
    base = dict(
        exercise_id="x", name="X", movement_pattern="squat", modality="strength", laterality="bilateral",
        measure="reps", difficulty=1, primary_muscles=("quads",), secondary_muscles=(),
        equipment_options=(), contraindications=frozenset(), goal_tags=frozenset({"strength"}),
        impact_level="low", default_tempo=None, source_kind="in_house", library_version="lib-test",
    )
    base.update(overrides)
    return ExerciseRecord(**base)


# --- availability semantics: OR of AND-sets, empty means bodyweight -----------------------------


def test_bodyweight_is_always_available() -> None:
    assert record().is_available_with(frozenset())


def test_all_items_in_an_option_are_required() -> None:
    barbell = record(equipment_options=(frozenset({"barbell", "squat_rack"}),))
    assert not barbell.is_available_with(frozenset({"barbell"}))
    assert not barbell.is_available_with(frozenset({"squat_rack"}))
    assert barbell.is_available_with(frozenset({"barbell", "squat_rack", "dumbbell"}))


def test_any_one_option_is_enough() -> None:
    goblet = record(equipment_options=(frozenset({"dumbbell"}), frozenset({"kettlebell"})))
    assert goblet.is_available_with(frozenset({"kettlebell"}))
    assert goblet.is_available_with(frozenset({"dumbbell"}))
    assert not goblet.is_available_with(frozenset({"resistance_band"}))
    assert not goblet.is_available_with(frozenset())


# --- loading from the database -------------------------------------------------------------------


def test_library_reflects_the_seeded_rows(db_session) -> None:
    seed_library(db_session)
    library = get_library(db_session)

    by_id = library.by_id
    goblet = by_id["goblet_squat"]
    assert set(goblet.equipment_options) == {frozenset({"dumbbell"}), frozenset({"kettlebell"})}
    assert "knee:deep_flexion_loaded" in goblet.contraindications
    assert by_id["bodyweight_squat"].is_bodyweight
    assert by_id["barbell_back_squat"].equipment_options == (frozenset({"barbell", "squat_rack"}),)


def test_bench_substitutions_become_separate_options(db_session) -> None:
    seed_library(db_session)
    press = get_library(db_session).by_id["dumbbell_bench_press"]
    assert set(press.equipment_options) == {
        frozenset({"dumbbell", "flat_bench"}),
        frozenset({"dumbbell", "adjustable_bench"}),
    }
    assert not press.is_available_with(frozenset({"dumbbell"}))
    assert press.is_available_with(frozenset({"dumbbell", "adjustable_bench"}))


def test_inactive_exercises_are_not_in_the_library(db_session) -> None:
    seed_library(db_session)
    db_session.query(ExerciseDefinition).filter_by(exercise_id="goblet_squat").update({"is_active": False})
    db_session.commit()
    assert "goblet_squat" not in load_library(db_session).by_id


def test_available_with_filters_by_ownership(db_session) -> None:
    seed_library(db_session)
    library = get_library(db_session)

    bodyweight_only = {r.exercise_id for r in library.available_with([])}
    assert "bodyweight_squat" in bodyweight_only
    assert "goblet_squat" not in bodyweight_only

    with_dumbbells = {r.exercise_id for r in library.available_with(["dumbbell"])}
    assert bodyweight_only < with_dumbbells
    assert "goblet_squat" in with_dumbbells
    assert "dumbbell_bench_press" not in with_dumbbells  # needs a bench too


def test_snapshot_is_immutable(db_session) -> None:
    import dataclasses

    seed_library(db_session)
    first = get_library(db_session).exercises[0]
    try:
        first.name = "changed"
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("ExerciseRecord must be frozen")


# --- caching -------------------------------------------------------------------------------------


def test_library_is_cached_until_cleared(db_session) -> None:
    seed_library(db_session)
    first = get_library(db_session)
    assert get_library(db_session) is first

    db_session.query(ExerciseDefinition).filter_by(exercise_id="goblet_squat").update({"is_active": False})
    db_session.commit()
    assert "goblet_squat" in get_library(db_session).by_id  # still the cached snapshot

    clear_library_cache()
    assert "goblet_squat" not in get_library(db_session).by_id


def test_seeding_refreshes_the_cache(db_session) -> None:
    seed_library(db_session)
    stale = get_library(db_session)
    db_session.query(ExerciseDefinition).filter_by(exercise_id="goblet_squat").update({"is_active": False})
    db_session.commit()

    seed_library(db_session)  # reactivates the exercise and clears the cache

    fresh = get_library(db_session)
    assert fresh is not stale
    assert "goblet_squat" in fresh.by_id
