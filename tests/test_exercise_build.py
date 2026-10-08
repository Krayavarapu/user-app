"""Guards on the generated library: curation table sanity and JSON/rules consistency."""
from __future__ import annotations

import json
import re

import pytest

from app.scripts.build_exercise_library import parse_equipment, slugify
from app.scripts.exercise_curation import PICKS
from app.services.exercise_library.exercise_seed import DEFAULT_EXERCISES_PATH
from app.services.exercise_library.seed import DEFAULT_EQUIPMENT_PATH
from app.services.exercise_library.tagging import (
    derive_contraindications,
    derive_default_tempo,
    derive_goal_tags,
    derive_impact_level,
)

CATALOG = {i["equipment_id"] for i in json.loads(DEFAULT_EQUIPMENT_PATH.read_text())["equipment"]}
EXERCISES = json.loads(DEFAULT_EXERCISES_PATH.read_text())["exercises"]


# --- equipment DSL ---------------------------------------------------------------------------------


def test_bodyweight_has_no_options() -> None:
    assert parse_equipment("") == []


def test_and_is_plus_and_or_is_pipe() -> None:
    assert parse_equipment("barbell+squat_rack") == [["barbell", "squat_rack"]]
    assert parse_equipment("dumbbell|kettlebell") == [["dumbbell"], ["kettlebell"]]


def test_bench_and_step_expand_to_every_acceptable_substitute() -> None:
    assert parse_equipment("dumbbell+BENCH") == [["adjustable_bench", "dumbbell"], ["dumbbell", "flat_bench"]]
    assert {i for option in parse_equipment("STEP") for i in option} == {"plyo_box", "flat_bench", "adjustable_bench"}
    assert len(parse_equipment("STEP")) == 3


def test_slugify() -> None:
    assert slugify("Farmer's Carry") == "farmers_carry"
    assert slugify("Hamstring Stretch (90/90)") == "hamstring_stretch_90_90"


# --- curation table --------------------------------------------------------------------------------


def test_curation_ids_are_unique_and_valid() -> None:
    ids = [slugify(p.name) for p in PICKS]
    assert len(ids) == len(set(ids))
    assert all(re.match(r"^[a-z][a-z0-9_]{2,63}$", i) for i in ids)


def test_curation_only_uses_catalog_equipment() -> None:
    used = {i for p in PICKS for option in parse_equipment(p.equipment) for i in option}
    assert used <= CATALOG


def test_in_house_picks_declare_their_muscles() -> None:
    for pick in PICKS:
        if pick.source is None:
            assert pick.muscles, pick.name


def test_each_source_entry_is_used_at_most_once() -> None:
    sources = [p.source for p in PICKS if p.source]
    assert len(sources) == len(set(sources))


# --- the committed JSON must be what the rules produce ---------------------------------------------


@pytest.mark.parametrize("entry", EXERCISES, ids=lambda e: e["exercise_id"])
def test_derived_fields_match_the_tagging_rules(entry) -> None:
    """Derived fields are never hand-edited: change a rule (or a pick) and rebuild instead."""
    equipment = sorted({i for option in entry["equipment_options"] for i in option})
    assert entry["impact_level"] == derive_impact_level(entry["name"])
    assert entry["contraindications"] == derive_contraindications(
        name=entry["name"],
        pattern=entry["movement_pattern"],
        laterality=entry["laterality"],
        equipment=equipment,
        impact_level=entry["impact_level"],
    )
    assert entry["goal_tags"] == derive_goal_tags(
        pattern=entry["movement_pattern"],
        modality=entry["modality"],
        equipment=equipment,
        difficulty=entry["difficulty"],
        impact_level=entry["impact_level"],
    )
    assert entry["default_tempo"] == derive_default_tempo(
        name=entry["name"], pattern=entry["movement_pattern"], modality=entry["modality"], measure=entry["measure"]
    )


def test_every_curated_pick_is_in_the_json_and_vice_versa() -> None:
    assert [e["exercise_id"] for e in EXERCISES] == [slugify(p.name) for p in PICKS]
