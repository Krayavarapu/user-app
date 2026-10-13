from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional, Sequence

from sqlalchemy.orm import Session

from app.models.equipment import Equipment, UserEquipment
from app.models.user_profile import UserProfile
from app.schemas.profile import ProfileUpdate

logger = logging.getLogger(__name__)


def get_profile(db: Session, user_id: str) -> Optional[UserProfile]:
    return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()


def get_equipment_ids(db: Session, user_id: str) -> List[str]:
    """The user's saved equipment, limited to items still in the active catalog."""
    rows = (
        db.query(UserEquipment.equipment_id)
        .join(Equipment, Equipment.equipment_id == UserEquipment.equipment_id)
        .filter(UserEquipment.user_id == user_id, Equipment.is_active.is_(True))
        .order_by(UserEquipment.equipment_id)
        .all()
    )
    return [row[0] for row in rows]


def find_unknown_equipment_ids(db: Session, equipment_ids: Sequence[str]) -> List[str]:
    """IDs that are not in the active catalog (unknown, or retired from the seed file)."""
    if not equipment_ids:
        return []
    known = {
        row[0]
        for row in db.query(Equipment.equipment_id)
        .filter(Equipment.equipment_id.in_(list(equipment_ids)), Equipment.is_active.is_(True))
        .all()
    }
    return sorted(set(equipment_ids) - known)


def save_profile(db: Session, user_id: str, payload: ProfileUpdate) -> UserProfile:
    """Create or replace the profile and the user's equipment in ONE transaction.

    Either everything is saved or nothing is: a failure part-way (for example a database error
    while inserting equipment) rolls the whole change back, so a user is never left with new
    limitations but stale equipment, or the reverse.
    """
    now = datetime.now(timezone.utc)
    limitations = [
        {"code": item.code, "severity": item.severity.value, "notes": item.notes}
        for item in sorted(payload.limitations, key=lambda item: item.code)
    ]
    try:
        profile = get_profile(db, user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id, created_at=now)
        profile.experience_level = payload.experience_level.value
        profile.primary_goal = payload.primary_goal.value if payload.primary_goal else None
        profile.days_per_week = payload.days_per_week
        profile.session_length_minutes = payload.session_length_minutes
        profile.limitations = limitations
        profile.updated_at = now
        db.add(profile)

        desired = set(payload.equipment_ids)
        owned_rows = db.query(UserEquipment).filter(UserEquipment.user_id == user_id).all()
        owned = {row.equipment_id for row in owned_rows}
        for row in owned_rows:
            if row.equipment_id not in desired:
                db.delete(row)
        for equipment_id in sorted(desired - owned):
            db.add(UserEquipment(user_id=user_id, equipment_id=equipment_id))

        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(profile)
    logger.info(
        "profile: saved user_id=%s limitations=%s equipment_count=%s",
        user_id,
        [(item["code"], item["severity"]) for item in limitations],
        len(desired),
    )
    return profile
