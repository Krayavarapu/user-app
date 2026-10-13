"""Safety rules: which exercises a user's limitations and experience level exclude.

This is the single place that turns "moderate shoulder limitation" into "never offer these
exercises". It is deliberately plain data plus two tiny pure functions so every line is easy to
review in a pull request and to unit-test.

IMPORTANT: these are conservative heuristics chosen by the app's authors. They have NOT been
reviewed by a coach or physical therapist and are not medical advice.

How it works
------------
* Each exercise carries ``region:stressor`` contraindication tags (see ``vocabulary.py``) and an
  ``impact_level``.
* A limitation is ``(code, severity)``. Severity is **cumulative**: severe excludes everything
  moderate does, and moderate everything mild does. The tables below list only what each level
  *adds*; ``LIMITATION_EXCLUSIONS`` is built cumulatively from them.
* ``LIMITATION_MAX_IMPACT`` additionally caps ``impact_level`` (``low`` < ``moderate`` < ``high``)
  for a few limitations at severe, which catches low-grade impact work (jumping jacks, jump rope)
  that carries no tag.
* Free-text notes never unlock or lock anything; only the structured codes here do.

Changing a rule: edit the increment tables, bump ``RULES_VERSION``, and update the tests, which
pin the behaviour per limitation and severity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Iterable, Mapping, Optional, Tuple

from app.services.exercise_library.vocabulary import CONTRAINDICATION_TAGS

RULES_VERSION = "rules-v1"

SEVERITIES: Tuple[str, str, str] = ("mild", "moderate", "severe")
IMPACT_ORDER: Dict[str, int] = {"low": 0, "moderate": 1, "high": 2}
DEFAULT_SEVERITY = "moderate"

# difficulty: 1 = beginner-friendly, 2 = needs some training experience, 3 = advanced
EXPERIENCE_MAX_DIFFICULTY: Dict[str, int] = {"beginner": 1, "intermediate": 2, "advanced": 3}

# What each severity ADDS to the one below it: (mild, moderate, severe).
_INCREMENTS: Dict[str, Tuple[FrozenSet[str], FrozenSet[str], FrozenSet[str]]] = {
    "shoulder": (
        frozenset({"shoulder:overhead_heavy", "shoulder:behind_neck"}),
        frozenset({"shoulder:overhead_loaded", "shoulder:dip"}),
        frozenset({"shoulder:overhead"}),
    ),
    "knee": (
        frozenset({"knee:high_impact"}),
        frozenset({"knee:pivoting", "knee:loaded_extension"}),
        frozenset({"knee:deep_flexion_loaded"}),
    ),
    "lower_back": (
        frozenset({"spine:axial_loading_heavy"}),
        frozenset({"spine:loaded_flexion", "spine:high_impact"}),
        frozenset({"spine:loaded_hinge"}),
    ),
    "wrist": (
        frozenset({"wrist:loaded_extension"}),
        frozenset({"wrist:weight_bearing"}),
        frozenset(),
    ),
    "hip": (
        frozenset({"hip:high_impact"}),
        frozenset({"hip:end_range"}),
        frozenset({"hip:deep_flexion_loaded"}),
    ),
    "ankle": (
        frozenset({"ankle:high_impact"}),
        frozenset({"ankle:single_leg_balance"}),
        frozenset({"ankle:loaded_plantarflexion"}),
    ),
    # The library has no resisted neck exercises, so mild changes nothing today; moderate removes
    # the loaded work that sits on or above the neck.
    "neck": (
        frozenset({"neck:loaded"}),
        frozenset({"shoulder:overhead_heavy", "spine:axial_loading_heavy"}),
        frozenset(),
    ),
}

# Highest impact_level still allowed, by (code, severity). Absent => no cap.
LIMITATION_MAX_IMPACT: Dict[Tuple[str, str], str] = {
    ("knee", "severe"): "low",
    ("hip", "severe"): "low",
    ("ankle", "severe"): "low",
}


def _cumulative(increments: Tuple[FrozenSet[str], ...]) -> Dict[str, FrozenSet[str]]:
    result: Dict[str, FrozenSet[str]] = {}
    accumulated: FrozenSet[str] = frozenset()
    for severity, added in zip(SEVERITIES, increments):
        accumulated = accumulated | added
        result[severity] = accumulated
    return result


LIMITATION_EXCLUSIONS: Dict[str, Dict[str, FrozenSet[str]]] = {
    code: _cumulative(increments) for code, increments in _INCREMENTS.items()
}

LIMITATION_CODES: FrozenSet[str] = frozenset(LIMITATION_EXCLUSIONS)


def _check_tables() -> None:
    """Fail at import time, not at plan time, if a rule references a tag that doesn't exist."""
    for code, increments in _INCREMENTS.items():
        for added in increments:
            unknown = added - CONTRAINDICATION_TAGS
            if unknown:
                raise RuntimeError(f"rules for {code!r} reference unknown tags: {sorted(unknown)}")
    for (code, severity), level in LIMITATION_MAX_IMPACT.items():
        if code not in LIMITATION_EXCLUSIONS or severity not in SEVERITIES or level not in IMPACT_ORDER:
            raise RuntimeError(f"invalid impact cap {(code, severity)!r}: {level!r}")


_check_tables()


@dataclass(frozen=True)
class Exclusions:
    """The combined effect of a user's limitations on the exercise library."""

    tags: FrozenSet[str] = frozenset()
    max_impact: Optional[str] = None  # None => no cap

    def excludes(self, contraindications: Iterable[str], impact_level: str) -> bool:
        if self.tags.intersection(contraindications):
            return True
        if self.max_impact is not None and IMPACT_ORDER[impact_level] > IMPACT_ORDER[self.max_impact]:
            return True
        return False


def exclusions_for(limitations: Iterable[Tuple[str, str]]) -> Exclusions:
    """Combine ``(code, severity)`` pairs into one ``Exclusions``.

    Unknown codes or severities raise ``ValueError`` rather than being ignored: silently skipping a
    limitation would quietly produce a less safe plan.
    """
    tags: set = set()
    cap: Optional[int] = None
    for code, severity in limitations:
        if code not in LIMITATION_EXCLUSIONS:
            raise ValueError(f"unknown limitation code: {code!r}")
        if severity not in SEVERITIES:
            raise ValueError(f"unknown limitation severity: {severity!r}")
        tags |= LIMITATION_EXCLUSIONS[code][severity]
        level = LIMITATION_MAX_IMPACT.get((code, severity))
        if level is not None:
            cap = IMPACT_ORDER[level] if cap is None else min(cap, IMPACT_ORDER[level])
    max_impact = None
    if cap is not None:
        max_impact = next(name for name, rank in IMPACT_ORDER.items() if rank == cap)
    return Exclusions(tags=frozenset(tags), max_impact=max_impact)


def max_difficulty_for(experience_level: str) -> int:
    try:
        return EXPERIENCE_MAX_DIFFICULTY[experience_level]
    except KeyError:
        raise ValueError(f"unknown experience level: {experience_level!r}") from None


def describe_limitation_rules() -> Mapping[str, Mapping[str, Tuple[str, ...]]]:
    """Sorted, serialisable view of the rules (used by tests and docs)."""
    return {
        code: {severity: tuple(sorted(tags)) for severity, tags in by_severity.items()}
        for code, by_severity in LIMITATION_EXCLUSIONS.items()
    }
