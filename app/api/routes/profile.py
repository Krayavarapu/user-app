from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_authenticated_user, get_current_user_id
from app.crud.profile import find_unknown_equipment_ids, get_equipment_ids, get_profile, save_profile
from app.database import get_db
from app.models.user_profile import UserProfile
from app.schemas.profile import (
    DEFAULT_DAYS_PER_WEEK,
    DEFAULT_EXPERIENCE_LEVEL,
    DEFAULT_SESSION_LENGTH_MINUTES,
    LimitationRead,
    ProfileRead,
    ProfileUpdate,
)

logger = logging.getLogger(__name__)

# Always about the authenticated caller: there is no user_id in the path, so one user can never
# read or write another's profile.
router = APIRouter(prefix="/users/me/profile", tags=["profile"])


def _to_read(profile: UserProfile, equipment_ids: list) -> ProfileRead:
    return ProfileRead(
        experience_level=profile.experience_level,
        primary_goal=profile.primary_goal,
        days_per_week=profile.days_per_week,
        session_length_minutes=profile.session_length_minutes,
        limitations=[LimitationRead(**item) for item in (profile.limitations or [])],
        equipment_ids=equipment_ids,
        is_default=False,
        updated_at=profile.updated_at,
    )


@router.get("", response_model=ProfileRead)
def get_profile_endpoint(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ProfileRead:
    """The caller's profile, or the conservative defaults (``is_default=true``) if never saved."""
    get_authenticated_user(db, current_user_id)
    equipment_ids = get_equipment_ids(db, current_user_id)
    profile = get_profile(db, current_user_id)
    if profile is None:
        return ProfileRead(
            experience_level=DEFAULT_EXPERIENCE_LEVEL,
            primary_goal=None,
            days_per_week=DEFAULT_DAYS_PER_WEEK,
            session_length_minutes=DEFAULT_SESSION_LENGTH_MINUTES,
            limitations=[],
            equipment_ids=equipment_ids,
            is_default=True,
            updated_at=None,
        )
    return _to_read(profile, equipment_ids)


@router.put("", response_model=ProfileRead)
def put_profile_endpoint(
    payload: ProfileUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> ProfileRead:
    """Replace the caller's profile and equipment atomically."""
    get_authenticated_user(db, current_user_id)

    unknown = find_unknown_equipment_ids(db, payload.equipment_ids)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown equipment ids: {', '.join(unknown)}. Use GET /equipment for valid ids.",
        )

    try:
        profile = save_profile(db, current_user_id, payload)
    except IntegrityError as exc:
        # Two saves racing to create the same profile; the loser can simply retry.
        logger.warning("profile: concurrent save conflict user_id=%s", current_user_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Your profile was updated at the same time. Please try again.",
        ) from exc
    return _to_read(profile, get_equipment_ids(db, current_user_id))
