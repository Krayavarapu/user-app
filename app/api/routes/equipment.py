from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.crud.equipment import list_active_equipment
from app.database import get_db
from app.schemas.equipment import EquipmentRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.get("", response_model=List[EquipmentRead])
def list_equipment_endpoint(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> List[EquipmentRead]:
    """Active equipment catalog, ordered by category then name (for a multi-select)."""
    rows = list_active_equipment(db)
    logger.debug("equipment: list user_id=%s count=%s", current_user_id, len(rows))
    return rows
