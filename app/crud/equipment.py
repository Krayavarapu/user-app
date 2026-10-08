from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.services.exercise_library.equipment_aliases import EquipmentAliasSource


def list_active_equipment(db: Session) -> List[Equipment]:
    return (
        db.query(Equipment)
        .filter(Equipment.is_active.is_(True))
        .order_by(Equipment.category, Equipment.name)
        .all()
    )


def list_alias_sources(db: Session) -> List[EquipmentAliasSource]:
    return [
        EquipmentAliasSource(equipment_id=row.equipment_id, name=row.name, aliases=list(row.aliases or []))
        for row in list_active_equipment(db)
    ]
