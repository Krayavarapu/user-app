from __future__ import annotations

import os


class Settings:
    @property
    def openai_api_key(self) -> str:
        return os.getenv("OPENAI_API_KEY", "").strip()

    @property
    def openai_model(self) -> str:
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

    @property
    def plan_generation_timeout_seconds(self) -> float:
        raw = os.getenv("PLAN_GENERATION_TIMEOUT_SECONDS", "120").strip()
        try:
            return max(1.0, float(raw))
        except ValueError:
            return 120.0


settings = Settings()
