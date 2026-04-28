from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session, selectinload

from app.models.fitness_plan import FitnessPlan
from app.models.plan_day import PlanDay
from app.schemas.plan import DayWorkout, PlanResponse


def create_plan(
    db: Session,
    *,
    plan_id: str,
    user_id: str,
    title: str,
    summary: str,
    prompt: str,
    goal: str,
    equipment: str,
    duration_days: int,
    notes: str,
    provider: str,
    generator_version: str,
    days: list[DayWorkout],
) -> FitnessPlan:
    now = datetime.now(timezone.utc)
    plan = FitnessPlan(
        plan_id=plan_id,
        user_id=user_id,
        title=title,
        summary=summary,
        prompt=prompt,
        goal=goal,
        equipment=equipment,
        duration_days=duration_days,
        notes=notes,
        provider=provider,
        generator_version=generator_version,
        status="active",
        generated_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(plan)
    db.flush()

    for day in days:
        db.add(
            PlanDay(
                plan_id=plan.plan_id,
                day_number=day.day_number,
                day_label=day.day_label,
                focus=day.focus,
                workout_json=json.dumps(day.exercises),
            )
        )

    db.commit()
    return get_plan_by_id(db, plan.plan_id)


def archive_user_active_plans(db: Session, user_id: str) -> None:
    active_plans = db.query(FitnessPlan).filter(FitnessPlan.user_id == user_id, FitnessPlan.status == "active").all()
    if not active_plans:
        return

    now = datetime.now(timezone.utc)
    for plan in active_plans:
        plan.status = "archived"
        plan.updated_at = now
        db.add(plan)
    db.commit()


def get_plan_by_id(db: Session, plan_id: str) -> Optional[FitnessPlan]:
    return (
        db.query(FitnessPlan)
        .options(selectinload(FitnessPlan.days))
        .filter(FitnessPlan.plan_id == plan_id)
        .first()
    )


def get_active_plan_for_user(db: Session, user_id: str) -> Optional[FitnessPlan]:
    return (
        db.query(FitnessPlan)
        .options(selectinload(FitnessPlan.days))
        .filter(FitnessPlan.user_id == user_id, FitnessPlan.status == "active")
        .order_by(FitnessPlan.generated_at.desc())
        .first()
    )


def plan_to_response(plan: FitnessPlan) -> PlanResponse:
    ordered_days = sorted(plan.days, key=lambda day: day.day_number)
    return PlanResponse(
        plan_id=plan.plan_id,
        title=plan.title,
        summary=plan.summary,
        duration_days=plan.duration_days,
        generated_at=plan.generated_at,
        notes=plan.notes or None,
        days=[
            DayWorkout(
                day_number=day.day_number,
                day_label=day.day_label,
                focus=day.focus,
                exercises=json.loads(day.workout_json),
            )
            for day in ordered_days
        ],
    )
