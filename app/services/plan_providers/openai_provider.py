from __future__ import annotations

import json
import logging
from typing import Any, Dict

import httpx

logger = logging.getLogger(__name__)

from app.models.user import User
from app.schemas.plan import PlanRequestBase
from app.services.plan_providers.base import PlanProvider
from app.settings import settings


class OpenAIPlanProvider(PlanProvider):
    provider_name = "openai"
    generator_version = "openai-v1"

    def _extract_json(self, raw_text: str) -> Dict[str, Any]:
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()
        return json.loads(cleaned)

    def generate(
        self,
        *,
        user: User,
        payload: PlanRequestBase,
        is_regeneration: bool,
    ) -> Dict[str, Any]:
        if not settings.openai_api_key:
            logger.error("openai: missing OPENAI_API_KEY")
            raise RuntimeError("OPENAI_API_KEY is not configured")

        system_prompt = (
            "You are a fitness plan generation engine. "
            "Return only valid JSON with keys: title, summary, days, notes. "
            "days must be an array of objects: day_number, day_label, focus, exercises. "
            "exercises must be an array of 3-6 concise strings (each under 12 words). "
            "Keep wording compact to reduce output length."
        )
        user_prompt = (
            f"Generate a {payload.duration_days}-day fitness plan.\n"
            f"User profile: first_name={user.first_name}, last_name={user.last_name}, "
            f"height={user.height}, weight_lbs={user.weight_lbs}, gender={user.gender}.\n"
            f"Goal: {payload.goal}\n"
            f"Equipment: {payload.equipment}\n"
            f"Prompt: {payload.prompt}\n"
            f"Regeneration: {'yes' if is_regeneration else 'no'}\n"
            "Ensure all day_number values are sequential starting at 1 and include exactly the requested number of days."
        )

        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openai_model,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
            },
            timeout=settings.plan_generation_timeout_seconds,
        )
        if response.status_code >= 400:
            logger.error(
                "openai: HTTP %s body_snippet=%r",
                response.status_code,
                (response.text or "")[:2000],
            )
        response.raise_for_status()
        body = response.json()
        usage = body.get("usage") or {}
        logger.info(
            "openai: ok id=%s model=%s prompt_tokens=%s completion_tokens=%s",
            body.get("id"),
            body.get("model"),
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
        )
        content = body["choices"][0]["message"]["content"]
        logger.debug("openai: content_chars=%s", len(content or ""))
        return self._extract_json(content)
