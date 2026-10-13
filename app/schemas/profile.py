from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, validator

from app.services.plan_pipeline.rules import DEFAULT_SEVERITY, LIMITATION_CODES

DEFAULT_EXPERIENCE_LEVEL = "beginner"
DEFAULT_DAYS_PER_WEEK = 3
DEFAULT_SESSION_LENGTH_MINUTES = 45


class ExperienceLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class LimitationSeverity(str, Enum):
    mild = "mild"
    moderate = "moderate"
    severe = "severe"


class PrimaryGoal(str, Enum):
    """Fixed goals used to rank exercises. A subset of the library's goal tags."""

    strength = "strength"
    hypertrophy = "hypertrophy"
    fat_loss = "fat_loss"
    endurance = "endurance"
    general_fitness = "general_fitness"
    mobility = "mobility"


class LimitationInput(BaseModel):
    """A structured limitation. Only ``code`` and ``severity`` affect which exercises are offered;
    ``notes`` is context for the plan prompt and never unlocks or locks anything."""

    code: str = Field(min_length=1, max_length=40)
    severity: LimitationSeverity = LimitationSeverity(DEFAULT_SEVERITY)
    notes: Optional[str] = Field(default=None, max_length=200)

    @validator("code", pre=True)
    def _known_code(cls, value):
        code = value.strip().lower() if isinstance(value, str) else value
        if code not in LIMITATION_CODES:
            raise ValueError(f"unknown limitation code; allowed: {', '.join(sorted(LIMITATION_CODES))}")
        return code

    @validator("notes")
    def _blank_notes_is_none(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None


class ProfileUpdate(BaseModel):
    """Full replacement of the caller's profile.

    ``limitations`` and ``equipment_ids`` are required (send ``[]`` for none) so that omitting one
    can never silently erase safety-relevant data. Unknown fields are rejected for the same
    reason: a misspelled ``limitation`` would otherwise be dropped without a trace.
    """

    experience_level: ExperienceLevel = ExperienceLevel(DEFAULT_EXPERIENCE_LEVEL)
    primary_goal: Optional[PrimaryGoal] = None
    days_per_week: int = Field(default=DEFAULT_DAYS_PER_WEEK, ge=1, le=7)
    session_length_minutes: int = Field(default=DEFAULT_SESSION_LENGTH_MINUTES, ge=15, le=120)
    limitations: List[LimitationInput] = Field(..., max_items=10)
    equipment_ids: List[str] = Field(..., max_items=40)

    class Config:
        extra = "forbid"

    @validator("limitations")
    def _no_duplicate_codes(cls, value: List[LimitationInput]) -> List[LimitationInput]:
        codes = [item.code for item in value]
        duplicates = sorted({code for code in codes if codes.count(code) > 1})
        if duplicates:
            raise ValueError(f"each limitation may appear once; repeated: {', '.join(duplicates)}")
        return value

    @validator("equipment_ids", each_item=True, pre=True)
    def _normalize_equipment_id(cls, value):
        if not isinstance(value, str):
            raise ValueError("equipment ids must be strings")
        value = value.strip().lower()
        if not value or len(value) > 40:
            raise ValueError("invalid equipment id")
        return value

    @validator("equipment_ids")
    def _dedupe_equipment(cls, value: List[str]) -> List[str]:
        return sorted(set(value))


class LimitationRead(BaseModel):
    # Plain strings: reading stored data must never fail because a rule was later retired.
    code: str
    severity: str
    notes: Optional[str] = None


class ProfileRead(BaseModel):
    experience_level: str
    primary_goal: Optional[str]
    days_per_week: int
    session_length_minutes: int
    limitations: List[LimitationRead]
    equipment_ids: List[str]
    # True when the user has never saved a profile: values above are the conservative defaults
    # that plan generation will use.
    is_default: bool
    updated_at: Optional[datetime] = None
