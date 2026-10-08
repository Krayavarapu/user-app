"""Controlled vocabularies for the exercise library.

Seed validation rejects any value outside these sets, so a typo in a tag can never silently
turn a safety exclusion into a no-op.

Contraindication tags are ``region:stressor``. Each exercise carries the tags describing the
stress it places on a body region. The *severity* at which a user limitation excludes a tag is
decided by the limitation rules (``plan_pipeline/rules.py``), not stored on the exercise. Regions
use ``spine`` for what users report as ``lower_back``.

Tag semantics (heuristics, applied by rule in ``tagging.py``; no clinical review):

shoulder
  overhead_heavy   barbell / Smith machine pressing overhead
  overhead_loaded  any other loaded work with the arms overhead (presses, overhead extensions,
                   pullovers, overhead carries, pike / handstand push-ups)
  behind_neck      any behind-the-neck press or pulldown
  overhead         hanging or pulling from overhead (pull-ups, pulldowns), unloaded arm elevation
  dip              dips (bench, parallel bar, ring)
knee
  high_impact          jumping / landing / bounding
  deep_flexion_loaded  loaded squats, lunges and step-ups
  loaded_extension     open-chain knee extension (leg extension)
  pivoting             lateral / twisting / cutting lower-body movement
spine
  axial_loading_heavy  barbell or Smith machine loading through the spine (squats, deadlifts,
                       overhead presses, bent-over rows)
  loaded_flexion       loaded trunk flexion / side bending
  high_impact          jumping / landing / bounding
wrist
  loaded_extension  wrist curls, front-rack positions
  weight_bearing    hands-on-floor support (push-ups, bear crawls, burpees, dips)
hip
  high_impact          jumping / landing / bounding
  deep_flexion_loaded  loaded squats
  end_range            wide-stance or end-range hip positions (sumo, cossack, groin stretches)
ankle
  high_impact         jumping / landing / bounding
  loaded_plantarflexion  calf raises
  single_leg_balance  single-leg stance work (single-leg deadlifts, lunges, step-ups)
neck
  loaded  resisted neck work
"""

from __future__ import annotations

import re
from typing import FrozenSet

CONTRAINDICATION_TAGS: FrozenSet[str] = frozenset(
    {
        "shoulder:overhead_heavy",
        "shoulder:overhead_loaded",
        "shoulder:behind_neck",
        "shoulder:overhead",
        "shoulder:dip",
        "knee:high_impact",
        "knee:deep_flexion_loaded",
        "knee:loaded_extension",
        "knee:pivoting",
        "spine:axial_loading_heavy",
        "spine:loaded_flexion",
        "spine:high_impact",
        "wrist:loaded_extension",
        "wrist:weight_bearing",
        "hip:high_impact",
        "hip:deep_flexion_loaded",
        "hip:end_range",
        "ankle:high_impact",
        "ankle:loaded_plantarflexion",
        "ankle:single_leg_balance",
        "neck:loaded",
    }
)

GOAL_TAGS: FrozenSet[str] = frozenset(
    {"strength", "hypertrophy", "endurance", "fat_loss", "power", "mobility", "general_fitness"}
)

MUSCLES: FrozenSet[str] = frozenset(
    {
        "abs", "obliques", "abductors", "adductors", "biceps", "calves", "chest", "core", "delts",
        "rear_delts", "forearms", "full_body", "glutes", "hamstrings", "hip_flexors", "hips", "lats",
        "lower_back", "mid_back", "upper_back", "neck", "quads", "thoracic_spine", "traps", "triceps",
    }
)

# Source-dataset muscle names -> our vocabulary.
SOURCE_MUSCLE_MAP = {
    "abdominals": "abs",
    "quadriceps": "quads",
    "middle back": "mid_back",
    "lower back": "lower_back",
    "shoulders": "delts",
}

TEMPO_PATTERN = re.compile(r"^[0-9X]{4}$")
EXERCISE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
