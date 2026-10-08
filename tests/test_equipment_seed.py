from __future__ import annotations

import json

import pytest

from app.models.equipment import Equipment
from app.services.exercise_library.seed import (
    DEFAULT_EQUIPMENT_PATH,
    SeedValidationError,
    load_equipment_seed,
    seed_equipment,
)


def write_seed(tmp_path, items, name="equipment.json"):
    path = tmp_path / name
    path.write_text(json.dumps({"library_version": "lib-test", "equipment": items}), encoding="utf-8")
    return path


def item(equipment_id, name=None, category="free_weights", aliases=()):
    return {
        "equipment_id": equipment_id,
        "name": name or equipment_id.replace("_", " ").title(),
        "category": category,
        "aliases": list(aliases),
    }


def snapshot(db):
    return {
        row.equipment_id: (row.name, row.category, row.aliases, row.is_active)
        for row in db.query(Equipment).order_by(Equipment.equipment_id).all()
    }


# --- the shipped seed file -------------------------------------------------------------------


def test_shipped_seed_file_is_valid() -> None:
    seed = load_equipment_seed(DEFAULT_EQUIPMENT_PATH)
    assert seed.library_version == "lib-v1"
    assert len(seed.equipment) >= 25


def test_shipped_seed_covers_equipment_named_in_the_design_doc() -> None:
    ids = {entry.equipment_id for entry in load_equipment_seed().equipment}
    assert {"dumbbell", "kettlebell", "barbell", "flat_bench", "squat_rack", "resistance_band"} <= ids


def test_shipped_seed_has_no_ambiguous_aliases() -> None:
    # load_equipment_seed raises on collisions; this documents the guarantee explicitly.
    load_equipment_seed()


# --- seeding behaviour ------------------------------------------------------------------------


def test_seed_creates_all_rows(db_session) -> None:
    result = seed_equipment(db_session)
    expected = len(load_equipment_seed().equipment)
    assert result.created == expected
    assert result.changed
    assert db_session.query(Equipment).count() == expected
    assert db_session.query(Equipment).filter(Equipment.is_active.is_(False)).count() == 0


def test_seed_is_idempotent(db_session) -> None:
    seed_equipment(db_session)
    first = snapshot(db_session)

    result = seed_equipment(db_session)
    assert not result.changed
    assert result.unchanged == len(first)
    assert snapshot(db_session) == first


def test_seed_updates_changed_rows_in_place(db_session, tmp_path) -> None:
    seed_equipment(db_session, write_seed(tmp_path, [item("dumbbell", aliases=["db"])]))

    result = seed_equipment(
        db_session,
        write_seed(tmp_path, [item("dumbbell", name="Dumbbell Pair", category="weights", aliases=["db", "dbs"])]),
    )
    assert (result.created, result.updated, result.unchanged) == (0, 1, 0)
    row = db_session.get(Equipment, "dumbbell")
    assert (row.name, row.category, row.aliases) == ("Dumbbell Pair", "weights", ["db", "dbs"])


def test_removed_equipment_is_deactivated_not_deleted(db_session, tmp_path) -> None:
    seed_equipment(db_session, write_seed(tmp_path, [item("dumbbell"), item("barbell")]))

    result = seed_equipment(db_session, write_seed(tmp_path, [item("dumbbell")]))
    assert result.deactivated == 1
    assert db_session.get(Equipment, "barbell") is not None
    assert db_session.get(Equipment, "barbell").is_active is False
    assert db_session.get(Equipment, "dumbbell").is_active is True

    # Running again doesn't re-count it.
    assert seed_equipment(db_session, write_seed(tmp_path, [item("dumbbell")])).deactivated == 0


def test_equipment_returning_to_the_file_is_reactivated(db_session, tmp_path) -> None:
    seed_equipment(db_session, write_seed(tmp_path, [item("dumbbell"), item("barbell")]))
    seed_equipment(db_session, write_seed(tmp_path, [item("dumbbell")]))

    result = seed_equipment(db_session, write_seed(tmp_path, [item("dumbbell"), item("barbell")]))
    assert (result.reactivated, result.created, result.updated) == (1, 0, 0)
    assert db_session.get(Equipment, "barbell").is_active is True


# --- validation -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "items, fragment",
    [
        ([item("dumbbell"), item("dumbbell", name="Other")], "duplicate equipment_id"),
        ([item("dumbbell", name="Same"), item("barbell", name="same")], "duplicate name"),
        ([item("dumbbell", aliases=["bar"]), item("barbell", aliases=["bar"])], "claimed by multiple items"),
        ([item("dumbbell", aliases=["   "])], "empty after normalization"),
        ([item("dumbbell", aliases=["no"])], "reserved word"),
        ([item("dumbbell", aliases=["Bodyweight"])], "reserved word"),
        ([item("Bad-Id")], "equipment_id"),
        ([], "equipment"),
    ],
)
def test_invalid_seed_files_are_rejected(db_session, tmp_path, items, fragment) -> None:
    with pytest.raises(SeedValidationError) as excinfo:
        seed_equipment(db_session, write_seed(tmp_path, items))
    assert fragment in str(excinfo.value)
    assert db_session.query(Equipment).count() == 0  # nothing partially applied


def test_alias_clashing_with_another_items_name_is_rejected(tmp_path) -> None:
    path = write_seed(tmp_path, [item("barbell", name="Barbell"), item("ez_bar", aliases=["barbell"])])
    with pytest.raises(SeedValidationError, match="claimed by multiple items"):
        load_equipment_seed(path)


def test_all_issues_are_reported_together(tmp_path) -> None:
    path = write_seed(
        tmp_path,
        [item("dumbbell", name="Same", aliases=["no"]), item("barbell", name="Same")],
    )
    with pytest.raises(SeedValidationError) as excinfo:
        load_equipment_seed(path)
    issues = " ".join(excinfo.value.issues)
    assert "reserved word" in issues
    assert "duplicate name" in issues
    assert len(excinfo.value.issues) >= 2  # reported together, not fail-fast


def test_missing_or_malformed_file_is_a_validation_error(tmp_path) -> None:
    with pytest.raises(SeedValidationError, match="cannot read"):
        load_equipment_seed(tmp_path / "nope.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(SeedValidationError, match="cannot read"):
        load_equipment_seed(bad)
