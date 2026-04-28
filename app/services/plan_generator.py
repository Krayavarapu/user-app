from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.models.user import User
from app.schemas.plan import PlanRequestBase, PlanResponse, WorkoutSection


def build_mock_plan(user: User, payload: PlanRequestBase, is_regeneration: bool = False) -> PlanResponse:
    plan_id = f"plan-{uuid4().hex[:12]}"
    first_name = user.first_name

    # Keep sections predictable and easy to replace later with AI generation.
    workouts = [
        WorkoutSection(
            name="Warm Up",
            duration_minutes=10,
            exercises=[
                "Light cardio (treadmill or brisk walk)",
                "Dynamic stretching",
            ],
        ),
        WorkoutSection(
            name="Main Block",
            duration_minutes=30,
            exercises=[
                f"Compound movement focused on {payload.goal}",
                f"Accessory circuit using: {payload.equipment}",
                "Core stability finisher",
            ],
        ),
        WorkoutSection(
            name="Cooldown",
            duration_minutes=10,
            exercises=[
                "Slow breathing",
                "Static stretching",
            ],
        ),
    ]

    regen_note = "Regenerated with updated preferences." if is_regeneration else None
    summary = (
        f"{first_name}, this plan is tailored for your goal '{payload.goal}' "
        f"using available equipment '{payload.equipment}'. Prompt context: {payload.prompt}"
    )

    return PlanResponse(
        plan_id=plan_id,
        title=f"{payload.goal.title()} Plan",
        summary=summary,
        workouts=workouts,
        generated_at=datetime.now(timezone.utc),
        notes=regen_note,
    )
