from __future__ import annotations

import logging
import time
from typing import Any, Dict, List
from uuid import uuid4

from app.models.user import User
from app.schemas.plan import DayWorkout, PlanRequestBase
from app.services.plan_providers import MockPlanProvider, OpenAIPlanProvider
from app.settings import settings

logger = logging.getLogger(__name__)


def _normalize_days(raw_days: Any, duration_days: int) -> List[DayWorkout]:
    normalized: List[DayWorkout] = []
    if not isinstance(raw_days, list):
        logger.debug(
            "normalize_days: raw_days is not a list (type=%s); treating as empty",
            type(raw_days).__name__,
        )
    source_days = raw_days if isinstance(raw_days, list) else []

    for day_number in range(1, duration_days + 1):
        source = source_days[day_number - 1] if day_number - 1 < len(source_days) else {}
        exercises = source.get("exercises") if isinstance(source, dict) else None
        if not isinstance(exercises, list):
            logger.debug(
                "normalize_days: day %s exercises not a list (type=%s); using defaults",
                day_number,
                type(exercises).__name__,
            )
            exercises = ["Main movement", "Accessory movement", "Cooldown"]
        cleaned_exercises = [str(item).strip() for item in exercises if str(item).strip()]
        if not cleaned_exercises:
            logger.debug(
                "normalize_days: day %s had no usable exercises after cleanup; using defaults",
                day_number,
            )
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
    title_raw = str(raw_plan.get("title", "")).strip()
    summary_raw = str(raw_plan.get("summary", "")).strip()
    if not title_raw:
        logger.debug("normalize_plan_fields: missing or empty title; using goal-based default")
    if not summary_raw:
        logger.debug("normalize_plan_fields: missing or empty summary; using template default")
    title = title_raw or f"{payload.goal.title()} Plan"
    summary = summary_raw or (
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
    t0 = time.perf_counter()
    openai_provider = OpenAIPlanProvider()
    mock_provider = MockPlanProvider()
    provider_used = mock_provider
    notes_prefix = ""

    logger.info(
        "plan_generator: start user_id=%s regeneration=%s goal=%r duration_days=%s model=%s",
        user.user_id,
        is_regeneration,
        payload.goal,
        payload.duration_days,
        settings.openai_model,
    )
    logger.debug(
        "plan_generator: request detail user_id=%s equipment=%r prompt_chars=%s openai_api_key_configured=%s",
        user.user_id,
        payload.equipment,
        len(payload.prompt or ""),
        bool(settings.openai_api_key),
    )

    try:
        raw_generated = openai_provider.generate(user=user, payload=payload, is_regeneration=is_regeneration)
        normalized = _normalize_plan_fields(raw_generated, payload)
        provider_used = openai_provider
        logger.debug(
            "plan_generator: OpenAI path ok user_id=%s raw_keys=%s",
            user.user_id,
            sorted(raw_generated.keys()) if isinstance(raw_generated, dict) else type(raw_generated).__name__,
        )
    except Exception:
        logger.warning(
            "plan_generator: primary provider failed; using mock fallback user_id=%s",
            user.user_id,
            exc_info=True,
        )
        raw_generated = mock_provider.generate(user=user, payload=payload, is_regeneration=is_regeneration)
        normalized = _normalize_plan_fields(raw_generated, payload)
        notes_prefix = "Generated using fallback provider. "

    notes = f"{notes_prefix}{normalized['notes']}".strip()
    elapsed = time.perf_counter() - t0
    plan_id = f"plan-{uuid4().hex[:12]}"

    logger.info(
        "plan_generator: done plan_id=%s user_id=%s provider=%s version=%s elapsed_s=%.3f days_count=%s",
        plan_id,
        user.user_id,
        provider_used.provider_name,
        provider_used.generator_version,
        elapsed,
        len(normalized["days"]),
    )

    return {
        "plan_id": plan_id,
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
