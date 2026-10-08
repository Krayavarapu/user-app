"""Rule-based enrichment for exercise definitions.

Contraindication tags, impact level, goal tags and default tempo are *derived by rule* from an
exercise's name, movement pattern, laterality and equipment rather than judged one exercise at a
time. Rules are consistent, reviewable in one place and unit-tested.

These are conservative heuristics, not clinical judgements; nothing here has been reviewed by a
coach or physical therapist (see docs/architecture/plan-generation-pipeline.md, open question 9).
Where a rule is unsure it errs towards tagging, since an extra tag only removes an exercise from a
menu for users who reported a related limitation.
"""

from __future__ import annotations

import re
from typing import FrozenSet, Iterable, List, Optional, Set

# Equipment that adds meaningful external load.
LOADED_EQUIPMENT: FrozenSet[str] = frozenset(
    {
        "barbell", "dumbbell", "kettlebell", "ez_bar", "weight_plate", "medicine_ball", "sandbag",
        "smith_machine", "cable_machine", "leg_press_machine",
    }
)
# Equipment that places a heavy bar on / over the spine.
BARBELL_LIKE: FrozenSet[str] = frozenset({"barbell", "smith_machine"})

_LOWER_BODY_PATTERNS = {"squat", "hinge", "lunge"}

# Word boundaries matter: "chop" contains "hop", "crunch" contains "run".
_UPPER_IMPACT = re.compile(r"\b(slam|throw|push-?up)\b")
_HIGH_IMPACT = re.compile(
    r"\bjump|\bhops?\b|\bbound(ing)?\b|\bleaps?\b|\bplyo|\bburpees?\b|\bskaters?\b|\bdepth\b|\bsprint"
)
_MODERATE_IMPACT = re.compile(
    r"\bhigh knees?\b|\bmountain climbers?\b|\bjog(ging)?\b|\brun(ning)?\b|\bslams?\b|\bskipping\b"
)

_WRIST_WEIGHT_BEARING = re.compile(
    r"push-?up|burpee|mountain climber|bear crawl|inchworm|handstand|pike|renegade|shoulder tap|"
    r"high plank|groiner|walk-?out|\bdips?\b"
)
_KNEE_PIVOTING = re.compile(
    r"lateral lunge|side lunge|cossack|curtsy|\bskaters?\b|carioca|agility|shuffle|lateral bound|pivot"
)
_HIP_END_RANGE = re.compile(r"sumo|plie|cossack|lateral lunge|side lunge|frog|straddle|groin|adductor|90/90")
_SINGLE_LEG_STANCE = re.compile(r"single-?\s?leg|one-?\s?legged|step-?up")

_TEMPO_BY_PATTERN = {
    "squat": "3010",
    "hinge": "3110",
    "lunge": "3010",
    "horizontal_push": "2010",
    "vertical_push": "2010",
    "horizontal_pull": "2011",
    "vertical_pull": "2011",
    "core_anti_extension": "2011",
    "core_anti_rotation": "2011",
    "core_flexion": "2011",
    "isolation_upper": "3010",
    "isolation_lower": "3010",
}
_NO_TEMPO = re.compile(r"swing|jump|slam|throw|burpee|hop|skater|clean|snatch")


def _has_loaded(equipment: Iterable[str]) -> bool:
    return bool(set(equipment) & LOADED_EQUIPMENT)


def derive_impact_level(name: str) -> str:
    """'low' | 'moderate' | 'high' from the exercise name."""
    lowered = name.lower()
    if re.search(r"jumping jack|jump rope|rope jump", lowered):
        return "moderate"
    if _HIGH_IMPACT.search(lowered):
        return "high"
    if _MODERATE_IMPACT.search(lowered):
        return "moderate"
    return "low"


def derive_contraindications(
    *,
    name: str,
    pattern: str,
    laterality: str,
    equipment: Iterable[str],
    impact_level: str,
) -> List[str]:
    """Contraindication tags (sorted) for one exercise. ``equipment`` is every item in any option."""
    n = name.lower()
    equip: Set[str] = set(equipment)
    loaded = _has_loaded(equip)
    barbell_like = bool(equip & BARBELL_LIKE)
    tags: Set[str] = set()

    # --- impact (jumping / landing) -------------------------------------------------------
    if impact_level == "high" and not _UPPER_IMPACT.search(n):
        tags |= {"knee:high_impact", "spine:high_impact", "hip:high_impact", "ankle:high_impact"}

    # --- shoulder -------------------------------------------------------------------------
    if "behind the neck" in n or "behind neck" in n:
        tags.add("shoulder:behind_neck")
    if pattern == "vertical_push":
        tags.add("shoulder:overhead_heavy" if barbell_like else "shoulder:overhead_loaded")
    elif "overhead" in n and loaded:
        tags.add("shoulder:overhead_loaded")
    if "pullover" in n:
        tags.add("shoulder:overhead_loaded")
    if pattern == "vertical_pull" or "hanging" in n:
        tags.add("shoulder:overhead")
    if re.search(r"\bdips?\b", n):
        tags.add("shoulder:dip")

    # --- knee / hip -----------------------------------------------------------------------
    if pattern in {"squat", "lunge"} and loaded:
        tags.add("knee:deep_flexion_loaded")
    if pattern == "squat" and loaded:
        tags.add("hip:deep_flexion_loaded")
    if "leg extension" in n:
        tags.add("knee:loaded_extension")
    if _KNEE_PIVOTING.search(n):
        tags.add("knee:pivoting")
    if _HIP_END_RANGE.search(n):
        tags.add("hip:end_range")

    # --- spine ----------------------------------------------------------------------------
    if barbell_like:
        if pattern in {"squat", "lunge"}:
            tags.add("spine:axial_loading_heavy")
        elif pattern == "hinge" and not re.search(r"hip thrust|glute bridge", n):
            tags.add("spine:axial_loading_heavy")
        elif pattern == "vertical_push":
            tags.add("spine:axial_loading_heavy")
        elif pattern == "horizontal_pull" and re.search(r"bent-?\s?over|t-bar", n):
            tags.add("spine:axial_loading_heavy")
    if pattern == "core_flexion" and loaded:
        tags.add("spine:loaded_flexion")

    # --- wrist ----------------------------------------------------------------------------
    if _WRIST_WEIGHT_BEARING.search(n):
        tags.add("wrist:weight_bearing")
    if "wrist curl" in n or "front squat" in n:
        tags.add("wrist:loaded_extension")

    # --- ankle ----------------------------------------------------------------------------
    if "calf raise" in n:
        tags.add("ankle:loaded_plantarflexion")
    # Lunges and split squats are single-leg-dominant; for squats and hinges only an explicit
    # single-leg variation counts (a one-arm swing still has both feet planted).
    if laterality in {"unilateral", "alternating"} and (
        pattern == "lunge"
        or (pattern in _LOWER_BODY_PATTERNS and _SINGLE_LEG_STANCE.search(n) and "bridge" not in n)
    ):
        tags.add("ankle:single_leg_balance")

    # --- neck -----------------------------------------------------------------------------
    if "neck" in n and re.search(r"isometric|resistance|harness", n):
        tags.add("neck:loaded")

    return sorted(tags)


def derive_goal_tags(
    *,
    pattern: str,
    modality: str,
    equipment: Iterable[str],
    difficulty: int,
    impact_level: str,
) -> List[str]:
    """Goal tags (sorted) used to rank the menu by the user's goal."""
    equip = set(equipment)
    if modality in {"warmup", "mobility"}:
        tags = {"mobility", "general_fitness"}
    elif modality == "conditioning":
        tags = {"endurance", "fat_loss", "general_fitness"}
        if impact_level == "high":
            tags.add("power")
    elif pattern in {"isolation_upper", "isolation_lower"}:
        tags = {"hypertrophy"}
    elif pattern.startswith("core_"):
        tags = {"general_fitness", "strength"}
    elif pattern == "carry":
        tags = {"strength", "endurance", "general_fitness"}
    elif equip:
        tags = {"strength", "hypertrophy", "general_fitness"}
    else:  # bodyweight strength work
        tags = {"general_fitness", "endurance", "hypertrophy"}
        if difficulty >= 2:
            tags.add("strength")
    return sorted(tags)


def derive_default_tempo(*, name: str, pattern: str, modality: str, measure: str) -> Optional[str]:
    """Four-digit tempo (eccentric, pause, concentric, pause), or None where tempo is meaningless."""
    if measure != "reps" or modality != "strength" or _NO_TEMPO.search(name.lower()):
        return None
    return _TEMPO_BY_PATTERN.get(pattern)
