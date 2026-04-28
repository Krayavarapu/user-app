from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PlanRequestBase(BaseModel):
    prompt: str = Field(min_length=1, max_length=500)
    goal: str = Field(min_length=1, max_length=120)
    equipment: str = Field(min_length=1, max_length=300)
    duration_days: int = Field(ge=1, le=90)


class PlanGenerateRequest(PlanRequestBase):
    pass


class PlanRegenerateRequest(PlanRequestBase):
    previous_plan_id: Optional[str] = Field(default=None, max_length=100)


class DayWorkout(BaseModel):
    day_number: int = Field(ge=1)
    day_label: str = Field(min_length=1, max_length=40)
    focus: str = Field(min_length=1, max_length=80)
    exercises: List[str] = Field(min_items=1, max_items=8)


class PlanResponse(BaseModel):
    plan_id: str
    title: str
    summary: str
    duration_days: int
    days: List[DayWorkout]
    generated_at: datetime
    notes: Optional[str] = None
