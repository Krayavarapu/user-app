from __future__ import annotations

from typing import Any, Dict, List
from uuid import uuid4

from app.models.user import User
from app.schemas.plan import DayWorkout, PlanRequestBase
from app.services.plan_providers import MockPlanProvider, OpenAIPlanProvider


def _normalize_days(raw_days: Any, duration_days: int) -> List[DayWorkout]:
    normalized: List[DayWorkout] = []
    source_days = raw_days if isinstance(raw_days, list) else []

    for day_number in range(1, duration_days + 1):
        source = source_days[day_number - 1] if day_number - 1 < len(source_days) else {}
        exercises = source.get("exercises") if isinstance(source, dict) else None
        if not isinstance(exercises, list):
            exercises = ["Main movement", "Accessory movement", "Cooldown"]
        cleaned_exercises = [str(item).strip() for item in exercises if str(item).strip()]
        if not cleaned_exercises:
            cleaned_exercises = ["Main movement", "Accessory movement", "Cooldown"]

        focus = source.get("focus") if isinstance(source, dict) else ""
        day_label = source.get("day_label") if isinstance(source, dict) else ""
        normalized.append(
            DayWorkout(
                day_number=day_number,
                day_label=str(day_label).strip() or f"Day {day_number}",
                focus=str(focus).strip() or f"Workout Day {day_number}",
                exercises=cleaned_exercises,
            )
        )
    return normalized


def _normalize_plan_fields(raw_plan: Dict[str, Any], payload: PlanRequestBase) -> Dict[str, Any]:
    title = str(raw_plan.get("title", "")).strip() or f"{payload.goal.title()} Plan"
    summary = str(raw_plan.get("summary", "")).strip() or (
        f"Plan focused on '{payload.goal}' using '{payload.equipment}' for {payload.duration_days} days."
    )
    notes = str(raw_plan.get("notes", "")).strip()
    return {
        "title": title,
        "summary": summary,
        "notes": notes,
        "days": _normalize_days(raw_plan.get("days"), payload.duration_days),
    }


def generate_plan_payload(user: User, payload: PlanRequestBase, is_regeneration: bool = False) -> dict:
    openai_provider = OpenAIPlanProvider()
    mock_provider = MockPlanProvider()
    provider_used = mock_provider
    notes_prefix = ""

    try:
        raw_generated = openai_provider.generate(user=user, payload=payload, is_regeneration=is_regeneration)
        normalized = _normalize_plan_fields(raw_generated, payload)
        provider_used = openai_provider
    except Exception:
        raw_generated = mock_provider.generate(user=user, payload=payload, is_regeneration=is_regeneration)
        normalized = _normalize_plan_fields(raw_generated, payload)
        notes_prefix = "Generated using fallback provider. "
        # print(f"Error generating plan: {e}")

    notes = f"{notes_prefix}{normalized['notes']}".strip()

    return {
        "plan_id": f"plan-{uuid4().hex[:12]}",
        "title": normalized["title"],
        "summary": normalized["summary"],
        "prompt": payload.prompt,
        "goal": payload.goal,
        "equipment": payload.equipment,
        "duration_days": payload.duration_days,
        "notes": notes,
        "days": normalized["days"],
        "provider": provider_used.provider_name,
        "generator_version": provider_used.generator_version,
    }
