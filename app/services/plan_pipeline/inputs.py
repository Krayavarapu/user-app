"""Resolve raw plan-request inputs into the structured values the pre-filter needs.

Only the free-text equipment matcher exists so far; profile/override resolution
(``resolve_inputs``) is added with the pre-filter.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.equipment import list_alias_sources
from app.services.exercise_library.equipment_aliases import EquipmentAliasIndex, EquipmentMatch

logger = logging.getLogger(__name__)


def match_free_text_equipment(db: Session, text: Optional[str]) -> EquipmentMatch:
    """Map the legacy free-text ``equipment`` field to catalog equipment IDs.

    Unmatched and negated terms are logged at DEBUG (term counts only, since free text may
    contain personal details) and never unlock exercises.
    """
    match = EquipmentAliasIndex(list_alias_sources(db)).match(text)
    logger.debug(
        "inputs: free-text equipment matched=%s unmatched_count=%s negated=%s",
        list(match.equipment_ids),
        len(match.unmatched_terms),
        list(match.negated_ids),
    )
    return match
