from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.models.user import User

logger = logging.getLogger(__name__)
from app.schemas.plan import PlanRequestBase
from app.services.plan_providers.base import PlanProvider


FOCUS_ROTATION = [
    "Upper Body Strength",
    "Lower Body Strength",
    "Cardio and Core",
    "Recovery and Mobility",
]


class MockPlanProvider(PlanProvider):
    provider_name = "mock"
    generator_version = "mock-v1"

    def _build_exercises(self, goal: str, equipment: str, focus: str) -> List[str]:
        return [
            f"Primary movement for {focus.lower()} aligned to goal: {goal}",
            f"Accessory set using available equipment: {equipment}",
            "Cooldown and stretching",
        ]

    def generate(
        self,
        *,
        user: User,
        payload: PlanRequestBase,
        is_regeneration: bool,
    ) -> Dict[str, Any]:
        logger.debug(
            "mock: generate user_id=%s goal=%r duration_days=%s regen=%s",
            user.user_id,
            payload.goal,
            payload.duration_days,
            is_regeneration,
        )
        first_name = user.first_name
        days: List[Dict[str, Any]] = []
        for day_number in range(1, payload.duration_days + 1):
            focus = FOCUS_ROTATION[(day_number - 1) % len(FOCUS_ROTATION)]
            days.append(
                {
                    "day_number": day_number,
                    "day_label": f"Day {day_number}",
                    "focus": focus,
                    "exercises": self._build_exercises(payload.goal, payload.equipment, focus),
                }
            )

        summary = (
            f"{first_name}, this plan is tailored for your goal '{payload.goal}' "
            f"using available equipment '{payload.equipment}' over {payload.duration_days} days. "
            f"Prompt context: {payload.prompt}"
        )

        notes = "Regenerated with updated preferences." if is_regeneration else ""
        return {
            "title": f"{payload.goal.title()} Plan",
            "summary": summary,
            "days": days,
            "notes": notes,
        }
