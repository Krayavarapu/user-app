from __future__ import annotations

import pytest

from app.services.exercise_library.tagging import (
    derive_contraindications,
    derive_default_tempo,
    derive_goal_tags,
    derive_impact_level,
)
from app.services.exercise_library.vocabulary import CONTRAINDICATION_TAGS


def tags(name, pattern, laterality="bilateral", equipment=(), impact=None):
    return set(
        derive_contraindications(
            name=name,
            pattern=pattern,
            laterality=laterality,
            equipment=equipment,
            impact_level=impact or derive_impact_level(name),
        )
    )


# --- impact: word boundaries (regression: "chop" contains "hop", "crunch" contains "run") -------


@pytest.mark.parametrize(
    "name",
    ["Cable Wood Chop", "Crunch", "Cable Crunch", "Bicycle Crunch", "Cable Crossover", "Plank", "Rowing Machine"],
)
def test_substring_lookalikes_are_not_impact(name) -> None:
    assert derive_impact_level(name) == "low"


@pytest.mark.parametrize("name", ["Box Jump", "Jump Squat", "Burpee", "Skaters", "Star Jump", "Split Jump"])
def test_jumping_movements_are_high_impact(name) -> None:
    assert derive_impact_level(name) == "high"


@pytest.mark.parametrize("name", ["Jumping Jacks", "Jump Rope", "High Knees", "Treadmill Jog", "Mountain Climber"])
def test_cardio_staples_are_moderate_impact(name) -> None:
    assert derive_impact_level(name) == "moderate"


def test_high_impact_tags_every_lower_body_joint_that_lands() -> None:
    assert {
        "knee:high_impact",
        "hip:high_impact",
        "ankle:high_impact",
        "spine:high_impact",
    } <= tags("Box Jump", "conditioning", equipment=["plyo_box"])


# --- shoulder -----------------------------------------------------------------------------------


def test_barbell_overhead_press_is_overhead_heavy_and_axial() -> None:
    result = tags("Barbell Standing Overhead Press", "vertical_push", equipment=["barbell", "squat_rack"])
    assert {"shoulder:overhead_heavy", "spine:axial_loading_heavy"} <= result
    assert "shoulder:overhead_loaded" not in result


def test_dumbbell_overhead_press_is_overhead_loaded_not_heavy() -> None:
    result = tags("Dumbbell Shoulder Press", "vertical_push", equipment=["dumbbell"])
    assert "shoulder:overhead_loaded" in result
    assert "shoulder:overhead_heavy" not in result
    assert "spine:axial_loading_heavy" not in result


def test_pull_ups_and_pulldowns_are_overhead() -> None:
    assert "shoulder:overhead" in tags("Pull-Up", "vertical_pull", equipment=["pull_up_bar"])
    assert "shoulder:overhead" in tags("Wide-Grip Lat Pulldown", "vertical_pull", equipment=["cable_machine"])


def test_dips_are_tagged() -> None:
    assert "shoulder:dip" in tags("Bench Dip", "horizontal_push", equipment=["flat_bench"])


def test_behind_the_neck_is_tagged() -> None:
    assert "shoulder:behind_neck" in tags("Behind The Neck Press", "vertical_push", equipment=["barbell"])


# --- knee / hip / ankle / spine / wrist ---------------------------------------------------------


def test_loaded_squats_and_lunges_flag_knee_but_bodyweight_does_not() -> None:
    assert "knee:deep_flexion_loaded" in tags("Goblet Squat", "squat", equipment=["dumbbell"])
    assert "knee:deep_flexion_loaded" in tags("Dumbbell Lunge", "lunge", "alternating", ["dumbbell"])
    assert "knee:deep_flexion_loaded" not in tags("Bodyweight Squat", "squat")


def test_barbell_squat_and_deadlift_are_axial_but_hip_thrust_is_not() -> None:
    assert "spine:axial_loading_heavy" in tags("Barbell Back Squat", "squat", equipment=["barbell"])
    assert "spine:axial_loading_heavy" in tags("Barbell Deadlift", "hinge", equipment=["barbell"])
    assert "spine:axial_loading_heavy" not in tags("Barbell Hip Thrust", "hinge", equipment=["barbell"])


def test_leg_extension_flags_the_knee() -> None:
    assert "knee:loaded_extension" in tags("Machine Leg Extension", "isolation_lower", equipment=["leg_extension_machine"])


def test_lateral_lunge_is_pivoting_and_end_range() -> None:
    result = tags("Bodyweight Lateral Lunge", "lunge", "alternating")
    assert {"knee:pivoting", "hip:end_range"} <= result


def test_cable_crossover_is_not_pivoting() -> None:
    # Regression: "crossover" used to match the knee-pivoting rule.
    assert "knee:pivoting" not in tags("Cable Crossover", "isolation_upper", equipment=["cable_machine"])


def test_single_leg_stance_only_for_genuine_single_leg_work() -> None:
    assert "ankle:single_leg_balance" in tags("Bodyweight Reverse Lunge", "lunge", "alternating")
    assert "ankle:single_leg_balance" in tags("Dumbbell Single-Leg Romanian Deadlift", "hinge", "unilateral", ["dumbbell"])
    # Regression: both feet are planted in a one-arm swing.
    assert "ankle:single_leg_balance" not in tags("One-Arm Kettlebell Swing", "hinge", "unilateral", ["kettlebell"])
    assert "ankle:single_leg_balance" not in tags("Single-Leg Glute Bridge", "hinge", "unilateral")


def test_calf_raises_load_the_ankle() -> None:
    assert "ankle:loaded_plantarflexion" in tags("Bodyweight Calf Raise", "isolation_lower")


def test_push_ups_and_planks_on_hands_bear_weight_through_the_wrist() -> None:
    assert "wrist:weight_bearing" in tags("Push-Up", "horizontal_push")
    assert "wrist:weight_bearing" in tags("Mountain Climber", "conditioning", "alternating")
    assert "wrist:weight_bearing" not in tags("Forearm Plank", "core_anti_extension")


def test_front_rack_and_wrist_curls_load_the_wrist() -> None:
    assert "wrist:loaded_extension" in tags("Barbell Front Squat", "squat", equipment=["barbell"])
    assert "wrist:loaded_extension" in tags("Dumbbell Wrist Curl", "isolation_upper", equipment=["dumbbell"])


def test_all_derived_tags_belong_to_the_vocabulary() -> None:
    samples = [
        ("Burpee", "conditioning", "bilateral", []),
        ("Barbell Standing Overhead Press", "vertical_push", "bilateral", ["barbell"]),
        ("Hanging Leg Raise", "core_flexion", "bilateral", ["pull_up_bar"]),
        ("Cable Crunch", "core_flexion", "bilateral", ["cable_machine"]),
        ("Dumbbell Bulgarian Split Squat", "lunge", "unilateral", ["dumbbell"]),
    ]
    for name, pattern, laterality, equipment in samples:
        assert tags(name, pattern, laterality, equipment) <= CONTRAINDICATION_TAGS


def test_output_is_sorted_and_deterministic() -> None:
    first = derive_contraindications(
        name="Barbell Back Squat", pattern="squat", laterality="bilateral", equipment=["barbell"], impact_level="low"
    )
    assert first == sorted(first)


# --- goal tags and tempo -------------------------------------------------------------------------


def test_goal_tags_follow_modality() -> None:
    assert "mobility" in derive_goal_tags(
        pattern="mobility", modality="warmup", equipment=[], difficulty=1, impact_level="low"
    )
    assert "fat_loss" in derive_goal_tags(
        pattern="conditioning", modality="conditioning", equipment=[], difficulty=1, impact_level="low"
    )
    assert "hypertrophy" in derive_goal_tags(
        pattern="isolation_upper", modality="strength", equipment=["dumbbell"], difficulty=1, impact_level="low"
    )


def test_every_exercise_gets_at_least_one_goal_tag() -> None:
    for pattern in ("squat", "carry", "core_flexion", "isolation_lower"):
        assert derive_goal_tags(pattern=pattern, modality="strength", equipment=[], difficulty=1, impact_level="low")


def test_tempo_only_for_controlled_rep_based_strength_work() -> None:
    assert derive_default_tempo(name="Goblet Squat", pattern="squat", modality="strength", measure="reps") == "3010"
    assert derive_default_tempo(name="Plank", pattern="core_anti_extension", modality="strength", measure="time") is None
    assert derive_default_tempo(name="Kettlebell Swing", pattern="hinge", modality="strength", measure="reps") is None
    assert derive_default_tempo(name="Treadmill Jog", pattern="conditioning", modality="conditioning", measure="time") is None
