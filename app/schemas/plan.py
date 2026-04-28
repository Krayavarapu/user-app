from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PlanRequestBase(BaseModel):
    prompt: str = Field(min_length=1, max_length=500)
    goal: str = Field(min_length=1, max_length=120)
    equipment: str = Field(min_length=1, max_length=300)


class PlanGenerateRequest(PlanRequestBase):
    pass


class PlanRegenerateRequest(PlanRequestBase):
    previous_plan_id: Optional[str] = Field(default=None, max_length=100)


class WorkoutSection(BaseModel):
    name: str
    duration_minutes: int = Field(gt=0)
    exercises: List[str]


class PlanResponse(BaseModel):
    plan_id: str
    title: str
    summary: str
    workouts: List[WorkoutSection]
    generated_at: datetime
    notes: Optional[str] = None
