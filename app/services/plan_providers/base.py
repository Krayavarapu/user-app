from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from app.models.user import User
from app.schemas.plan import PlanRequestBase


class PlanProvider(ABC):
    provider_name: str = "unknown"
    generator_version: str = "v1"

    @abstractmethod
    def generate(
        self,
        *,
        user: User,
        payload: PlanRequestBase,
        is_regeneration: bool,
    ) -> Dict[str, Any]:
        """Return a raw generated plan dictionary."""
