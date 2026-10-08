from __future__ import annotations

import pytest

from app.services.exercise_library import equipment_aliases
from app.services.exercise_library.equipment_aliases import (
    EquipmentAliasIndex,
    EquipmentAliasSource,
    find_alias_collisions,
    normalize_text,
)
from app.services.exercise_library.seed import load_equipment_seed


@pytest.fixture(scope="module")
def index() -> EquipmentAliasIndex:
    seed = load_equipment_seed()
    return EquipmentAliasIndex(EquipmentAliasSource(i.equipment_id, i.name, i.aliases) for i in seed.equipment)


def ids(index: EquipmentAliasIndex, text) -> tuple:
    return index.match(text).equipment_ids


def test_normalize_text() -> None:
    assert normalize_text("  Pull-Up   BAR!! ") == "pull up bar"
    assert normalize_text("Don't have DB's") == "dont have dbs"
    assert normalize_text("") == ""


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Dumbbells", ("dumbbell",)),
        ("dumbbells", ("dumbbell",)),
        ("DB", ("dumbbell",)),
        ("dbs", ("dumbbell",)),
        ("Dumbbells, resistance bands, bench", ("dumbbell", "resistance_band", "flat_bench")),
        ("Dumbbells and yoga mat", ("dumbbell", "yoga_mat")),
        ("bands", ("resistance_band",)),
        ("Resistance bands only", ("resistance_band",)),
        ("kettlebells", ("kettlebell",)),
        ("DB/KB", ("dumbbell", "kettlebell")),
        ("TRX", ("suspension_trainer",)),
        ("pull-up bar", ("pull_up_bar",)),
        ("chin up bar", ("pull_up_bar",)),
        ("benches", ("flat_bench",)),
        ("I have a squat rack and a barbell", ("squat_rack", "barbell")),
    ],
)
def test_aliases_map_to_catalog_ids(index, text, expected) -> None:
    assert ids(index, text) == expected


def test_longest_phrase_wins_over_shorter_alias(index) -> None:
    # "adjustable bench" must not also unlock the flat "bench" alias.
    assert ids(index, "adjustable bench") == ("adjustable_bench",)
    assert ids(index, "adjustable bench and flat bench") == ("adjustable_bench", "flat_bench")


def test_results_are_deduplicated_and_ordered_by_first_mention(index) -> None:
    assert ids(index, "kettlebell, dumbbells, db, kettlebells") == ("kettlebell", "dumbbell")


@pytest.mark.parametrize("text", [None, "", "   ", "bodyweight", "Body weight", "none", "no equipment", "nothing"])
def test_empty_or_bodyweight_text_matches_nothing_without_unmatched_noise(index, text) -> None:
    match = index.match(text)
    assert match.equipment_ids == ()
    assert match.unmatched_terms == ()


def test_unmatched_terms_are_reported_and_never_unlock(index) -> None:
    match = index.match("a treadmil, some cool stuff, dumbbells")
    assert match.equipment_ids == ("dumbbell",)
    assert match.unmatched_terms == ("treadmil", "cool")


def test_generic_words_do_not_match_anything(index) -> None:
    # "bar" and "weights" are too ambiguous to map to a specific item.
    assert ids(index, "bar") == ()
    assert ids(index, "weights") == ()
    assert ids(index, "home gym") == ()
    # "bike" could be an outdoor bike; only explicit stationary-bike phrases match.
    assert ids(index, "bike") == ()
    assert ids(index, "spin bike") == ("stationary_bike",)


@pytest.mark.parametrize(
    "text, owned, negated",
    [
        ("no barbell", (), ("barbell",)),
        ("without a squat rack", (), ("squat_rack",)),
        ("I don't have dumbbells", (), ("dumbbell",)),
        ("I dont have a barbell", (), ("barbell",)),
        ("no barbell, just dumbbells", ("dumbbell",), ("barbell",)),
        ("kettlebell but no bench", ("kettlebell",), ("flat_bench",)),
        ("dumbbells and no bench", ("dumbbell",), ("flat_bench",)),
        ("everything except a barbell", (), ("barbell",)),
    ],
)
def test_negated_equipment_is_never_unlocked(index, text, owned, negated) -> None:
    match = index.match(text)
    assert match.equipment_ids == owned
    assert match.negated_ids == negated


def test_negation_covers_the_rest_of_the_clause_conservatively(index) -> None:
    # Under-matching is the safe direction: dumbbells here are dropped rather than risk unlocking.
    assert ids(index, "no barbell and dumbbells") == ()


def test_item_negated_anywhere_is_not_owned(index) -> None:
    assert ids(index, "dumbbells, no dumbbells") == ()


def test_negation_does_not_leak_across_clauses(index) -> None:
    assert ids(index, "no barbell; dumbbells. kettlebell") == ("dumbbell", "kettlebell")


def test_equipment_id_and_name_match_implicitly() -> None:
    source = EquipmentAliasSource(equipment_id="battle_rope", name="Battle Ropes", aliases=())
    index = EquipmentAliasIndex([source])
    assert index.match("battle rope").equipment_ids == ("battle_rope",)
    assert index.match("Battle Ropes").equipment_ids == ("battle_rope",)


def test_ambiguous_aliases_unlock_neither_item(monkeypatch) -> None:
    # app logging doesn't propagate to the root logger, so caplog can't see it; capture directly.
    warnings = []
    monkeypatch.setattr(equipment_aliases.logger, "warning", lambda msg, *args: warnings.append(msg % args))
    sources = [
        EquipmentAliasSource("barbell", "Barbell", ["bar"]),
        EquipmentAliasSource("pull_up_bar", "Pull-Up Bar", ["bar"]),
    ]
    assert find_alias_collisions(sources) == {"bar": {"barbell", "pull_up_bar"}}
    index = EquipmentAliasIndex(sources)
    assert index.match("bar").equipment_ids == ()
    # The unambiguous names still work.
    assert index.match("barbell, pull up bar").equipment_ids == ("barbell", "pull_up_bar")
    assert any("ambiguous alias dropped" in message and "'bar'" in message for message in warnings)
