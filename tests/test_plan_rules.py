from __future__ import annotations

import pytest

from app.services.exercise_library.exercise_seed import seed_library
from app.services.exercise_library.repository import get_library
from app.services.exercise_library.vocabulary import CONTRAINDICATION_TAGS
from app.services.plan_pipeline import rules
from app.services.plan_pipeline.rules import (
    EXPERIENCE_MAX_DIFFICULTY,
    LIMITATION_CODES,
    LIMITATION_EXCLUSIONS,
    SEVERITIES,
    exclusions_for,
    max_difficulty_for,
)


@pytest.fixture()
def library(db_session):
    seed_library(db_session)
    return get_library(db_session)


def removed(library, *limitations, owned=None):
    """Names of exercises removed by the given (code, severity) limitations."""
    exclusions = exclusions_for(limitations)
    pool = library.exercises if owned is None else library.available_with(owned)
    return {r.name for r in pool if exclusions.excludes(r.contraindications, r.impact_level)}


# --- the rule tables themselves ------------------------------------------------------------------


def test_supported_limitation_codes_are_the_approved_seven() -> None:
    assert LIMITATION_CODES == {"shoulder", "knee", "lower_back", "wrist", "hip", "ankle", "neck"}


def test_every_rule_references_only_vocabulary_tags() -> None:
    for code, by_severity in LIMITATION_EXCLUSIONS.items():
        for severity, tags in by_severity.items():
            assert tags <= CONTRAINDICATION_TAGS, (code, severity)


def test_severity_is_cumulative() -> None:
    for code, by_severity in LIMITATION_EXCLUSIONS.items():
        assert by_severity["mild"] <= by_severity["moderate"] <= by_severity["severe"], code


def test_every_vocabulary_tag_is_excluded_by_some_limitation() -> None:
    """A tag no rule uses would be a safety label that does nothing."""
    used = set().union(*(tags for by in LIMITATION_EXCLUSIONS.values() for tags in by.values()))
    assert CONTRAINDICATION_TAGS <= used, sorted(CONTRAINDICATION_TAGS - used)


def test_rules_are_versioned() -> None:
    assert rules.RULES_VERSION == "rules-v1"


# The approved mapping, pinned exactly. Changing a rule must be a deliberate edit to this table.
EXPECTED = {
    "shoulder": {
        "mild": {"shoulder:overhead_heavy", "shoulder:behind_neck"},
        "moderate": {"shoulder:overhead_loaded", "shoulder:dip"},
        "severe": {"shoulder:overhead"},
    },
    "knee": {
        "mild": {"knee:high_impact"},
        "moderate": {"knee:pivoting", "knee:loaded_extension"},
        "severe": {"knee:deep_flexion_loaded"},
    },
    "lower_back": {
        "mild": {"spine:axial_loading_heavy"},
        "moderate": {"spine:loaded_flexion", "spine:high_impact"},
        "severe": {"spine:loaded_hinge"},
    },
    "wrist": {
        "mild": {"wrist:loaded_extension"},
        "moderate": {"wrist:weight_bearing"},
        "severe": set(),
    },
    "hip": {
        "mild": {"hip:high_impact"},
        "moderate": {"hip:end_range"},
        "severe": {"hip:deep_flexion_loaded"},
    },
    "ankle": {
        "mild": {"ankle:high_impact"},
        "moderate": {"ankle:single_leg_balance"},
        "severe": {"ankle:loaded_plantarflexion"},
    },
    "neck": {
        "mild": {"neck:loaded"},
        "moderate": {"shoulder:overhead_heavy", "spine:axial_loading_heavy"},
        "severe": set(),
    },
}


@pytest.mark.parametrize("code", sorted(EXPECTED))
def test_mapping_matches_the_approved_table(code) -> None:
    accumulated: set = set()
    for severity in SEVERITIES:
        accumulated |= EXPECTED[code][severity]
        assert LIMITATION_EXCLUSIONS[code][severity] == accumulated, (code, severity)


def test_impact_caps_only_apply_to_severe_knee_hip_and_ankle() -> None:
    assert rules.LIMITATION_MAX_IMPACT == {
        ("knee", "severe"): "low",
        ("hip", "severe"): "low",
        ("ankle", "severe"): "low",
    }


# --- exclusions_for ------------------------------------------------------------------------------


def test_no_limitations_excludes_nothing() -> None:
    result = exclusions_for([])
    assert result.tags == frozenset() and result.max_impact is None
    assert not result.excludes(["knee:high_impact"], "high")


def test_unknown_code_or_severity_is_an_error_not_ignored() -> None:
    with pytest.raises(ValueError, match="unknown limitation code"):
        exclusions_for([("elbow", "mild")])
    with pytest.raises(ValueError, match="unknown limitation severity"):
        exclusions_for([("knee", "extreme")])


def test_multiple_limitations_union_their_tags_and_take_the_strictest_cap() -> None:
    result = exclusions_for([("shoulder", "mild"), ("knee", "severe"), ("ankle", "mild")])
    assert "shoulder:overhead_heavy" in result.tags and "knee:deep_flexion_loaded" in result.tags
    assert result.max_impact == "low"


def test_impact_cap_blocks_untagged_moderate_impact_exercises() -> None:
    result = exclusions_for([("knee", "severe")])
    assert result.excludes([], "moderate")
    assert result.excludes([], "high")
    assert not result.excludes([], "low")
    assert not exclusions_for([("knee", "moderate")]).excludes([], "moderate")


def test_experience_levels_map_to_a_difficulty_ceiling() -> None:
    assert EXPERIENCE_MAX_DIFFICULTY == {"beginner": 1, "intermediate": 2, "advanced": 3}
    assert max_difficulty_for("beginner") == 1
    with pytest.raises(ValueError):
        max_difficulty_for("expert")


# --- behaviour against the real library ---------------------------------------------------------


def test_shoulder_levels(library) -> None:
    mild = removed(library, ("shoulder", "mild"))
    assert "Barbell Standing Overhead Press" in mild
    assert "Dumbbell Shoulder Press" not in mild and "Pull-Up" not in mild

    moderate = removed(library, ("shoulder", "moderate"))
    assert {"Dumbbell Shoulder Press", "Bench Dip", "Overhead Carry"} <= moderate
    assert "Pull-Up" not in moderate and "Dumbbell Bench Press" not in moderate

    severe = removed(library, ("shoulder", "severe"))
    assert {"Pull-Up", "Wide-Grip Lat Pulldown", "Hanging Leg Raise"} <= severe


def test_knee_levels(library) -> None:
    mild = removed(library, ("knee", "mild"))
    assert {"Box Jump", "Burpee", "Jump Squat"} <= mild
    assert "Goblet Squat" not in mild

    moderate = removed(library, ("knee", "moderate"))
    assert {"Bodyweight Lateral Lunge", "Machine Leg Extension"} <= moderate
    assert "Goblet Squat" not in moderate

    severe = removed(library, ("knee", "severe"))
    assert {"Goblet Squat", "Dumbbell Lunge", "Leg Press", "Jump Rope", "Treadmill Jog", "High Knees"} <= severe
    assert {"Bodyweight Squat", "Glute Bridge", "Treadmill Walk", "Stationary Bike"}.isdisjoint(severe)


def test_lower_back_levels(library) -> None:
    mild = removed(library, ("lower_back", "mild"))
    assert {"Barbell Deadlift", "Barbell Back Squat", "Barbell Standing Overhead Press"} <= mild
    assert "Dumbbell Romanian Deadlift" not in mild

    moderate = removed(library, ("lower_back", "moderate"))
    assert {"Cable Crunch", "Dumbbell Side Bend", "Box Jump"} <= moderate
    assert "Dumbbell Romanian Deadlift" not in moderate

    severe = removed(library, ("lower_back", "severe"))
    assert {"Dumbbell Romanian Deadlift", "Kettlebell Swing", "Cable Pull-Through"} <= severe
    assert {"Glute Bridge", "Barbell Hip Thrust", "Floor Back Extension"}.isdisjoint(severe)


def test_wrist_levels(library) -> None:
    assert "Dumbbell Wrist Curl" in removed(library, ("wrist", "mild"))
    assert "Push-Up" not in removed(library, ("wrist", "mild"))
    moderate = removed(library, ("wrist", "moderate"))
    assert {"Push-Up", "Burpee", "Mountain Climber", "Bench Dip"} <= moderate
    assert "Dumbbell Bench Press" not in moderate
    assert removed(library, ("wrist", "severe")) == moderate


def test_hip_levels(library) -> None:
    assert "Box Jump" in removed(library, ("hip", "mild"))
    assert "Bodyweight Sumo Squat" in removed(library, ("hip", "moderate"))
    severe = removed(library, ("hip", "severe"))
    assert {"Goblet Squat", "Barbell Back Squat", "Jump Rope"} <= severe
    assert "Bodyweight Squat" not in severe


def test_ankle_levels(library) -> None:
    assert "Box Jump" in removed(library, ("ankle", "mild"))
    assert "Bodyweight Reverse Lunge" in removed(library, ("ankle", "moderate"))
    severe = removed(library, ("ankle", "severe"))
    assert {"Bodyweight Calf Raise", "Jumping Jacks"} <= severe
    assert "Bodyweight Squat" not in severe


def test_neck_levels(library) -> None:
    assert removed(library, ("neck", "mild")) == set()  # no resisted neck work in the library
    moderate = removed(library, ("neck", "moderate"))
    assert {"Barbell Standing Overhead Press", "Barbell Back Squat", "Barbell Deadlift"} <= moderate
    assert "Dumbbell Shoulder Press" not in moderate
    assert removed(library, ("neck", "severe")) == moderate


def test_removal_never_shrinks_as_severity_rises(library) -> None:
    for code in sorted(LIMITATION_CODES):
        sizes = [len(removed(library, (code, severity))) for severity in SEVERITIES]
        assert sizes == sorted(sizes), (code, sizes)


REQUIREMENTS = {
    "squat or lunge": lambda p: bool(p & {"squat", "lunge"}),
    "hinge": lambda p: "hinge" in p,
    "push": lambda p: bool(p & {"horizontal_push", "vertical_push"}),
    "pull": lambda p: bool(p & {"horizontal_pull", "vertical_pull"}),
    "core": lambda p: any(x.startswith("core_") for x in p),
}

# Menu gaps that are real, not bugs: with only bodyweight, a wrist limitation (moderate or worse)
# leaves no pushing exercise because every bodyweight push loads the hands. Phase 4 turns this
# into an InsufficientMenuError telling the user to add equipment; a resistance band is enough
# (see the next test). If the library gains a genuinely wrist-friendly bodyweight push, this
# entry must be removed (the test after next fails to remind you).
KNOWN_MENU_GAPS = {"wrist": {"push"}}


def unmet_requirements(library, code, owned):
    exclusions = exclusions_for([(code, "severe")])
    menu = [
        r
        for r in library.available_with(owned)
        if not exclusions.excludes(r.contraindications, r.impact_level)
    ]
    patterns = {r.movement_pattern for r in menu}
    unmet = {name for name, check in REQUIREMENTS.items() if not check(patterns)}
    if sum(1 for r in menu if r.modality == "warmup") < 2:
        unmet.add("warm-up")
    return unmet


def test_a_bodyweight_user_with_any_single_severe_limitation_gets_a_workable_menu(library) -> None:
    """Over-excluding is a failure too: doc section 8 needs a lower-body, hinge, push, pull and core
    option plus 2 warm-up items to build any plan at all."""
    unmet = {code: unmet_requirements(library, code, []) for code in sorted(LIMITATION_CODES)}
    assert {code: gaps for code, gaps in unmet.items() if gaps} == KNOWN_MENU_GAPS


def test_a_resistance_band_closes_every_known_menu_gap(library) -> None:
    for code in sorted(LIMITATION_CODES):
        assert not unmet_requirements(library, code, ["resistance_band"]), code


def test_known_menu_gaps_are_still_gaps(library) -> None:
    for code, gaps in KNOWN_MENU_GAPS.items():
        assert gaps <= unmet_requirements(library, code, []), f"{code} gap is fixed; remove it"
