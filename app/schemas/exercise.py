from __future__ import annotations

from enum import Enum


class MovementPattern(str, Enum):
    squat = "squat"
    hinge = "hinge"
    lunge = "lunge"
    horizontal_push = "horizontal_push"
    vertical_push = "vertical_push"
    horizontal_pull = "horizontal_pull"
    vertical_pull = "vertical_pull"
    carry = "carry"
    core_anti_extension = "core_anti_extension"
    core_anti_rotation = "core_anti_rotation"
    core_flexion = "core_flexion"
    conditioning = "conditioning"
    mobility = "mobility"
    # Single-joint accessory work (curls, lateral raises, calf raises, leg curls, ...). Not part of
    # the original design doc's pattern list: without them "build muscle" plans would have no
    # accessory options.
    isolation_upper = "isolation_upper"
    isolation_lower = "isolation_lower"


class Modality(str, Enum):
    strength = "strength"
    conditioning = "conditioning"
    mobility = "mobility"  # static stretching / cool-down
    warmup = "warmup"  # dynamic mobility, activation, foam rolling


class Measure(str, Enum):
    reps = "reps"
    time = "time"


class Laterality(str, Enum):
    bilateral = "bilateral"
    unilateral = "unilateral"
    alternating = "alternating"


class ImpactLevel(str, Enum):
    low = "low"
    moderate = "moderate"
    high = "high"
