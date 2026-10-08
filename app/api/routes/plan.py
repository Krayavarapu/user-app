from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_authenticated_user, get_current_user_id
from app.crud.plan import (
    archive_user_active_plans,
    create_plan,
    get_active_plan_for_user,
    get_plan_by_id,
    plan_to_response,
)
from app.database import get_db
from app.schemas.plan import PlanGenerateRequest, PlanRegenerateRequest, PlanResponse
from app.services.plan_generator import generate_plan_payload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plan", tags=["plan"])


def _replace_active_plan(db: Session, user_id: str, generated: dict):
    """Archive the current active plan and persist the new one in a single transaction.

    Generation must already have succeeded: if it fails, the user keeps their active plan.
    """
    try:
        archive_user_active_plans(db, user_id, commit=False)
        return create_plan(db, user_id=user_id, **generated)
    except Exception:
        db.rollback()
        raise


@router.post("/generate", response_model=PlanResponse)
def generate_plan_endpoint(
    payload: PlanGenerateRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PlanResponse:
    user = get_authenticated_user(db, current_user_id)
    generated = generate_plan_payload(user=user, payload=payload)
    plan = _replace_active_plan(db, user.user_id, generated)
    logger.info(
        "plan: generate ok plan_id=%s user_id=%s provider=%s",
        plan.plan_id,
        user.user_id,
        plan.provider,
    )
    return plan_to_response(plan)


@router.post("/regenerate", response_model=PlanResponse)
def regenerate_plan_endpoint(
    payload: PlanRegenerateRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PlanResponse:
    user = get_authenticated_user(db, current_user_id)
    if payload.previous_plan_id:
        previous = get_plan_by_id(db, payload.previous_plan_id)
        # Same response for "missing" and "someone else's" so plan IDs can't be probed.
        if not previous or previous.user_id != user.user_id:
            logger.info(
                "plan: regenerate rejected unknown previous_plan_id=%s user_id=%s",
                payload.previous_plan_id,
                user.user_id,
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    generated = generate_plan_payload(user=user, payload=payload, is_regeneration=True)
    plan = _replace_active_plan(db, user.user_id, generated)
    logger.info(
        "plan: regenerate ok plan_id=%s user_id=%s provider=%s",
        plan.plan_id,
        user.user_id,
        plan.provider,
    )
    return plan_to_response(plan)


@router.get("/active", response_model=PlanResponse)
def get_active_plan_endpoint(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PlanResponse:
    plan = get_active_plan_for_user(db, current_user_id)
    if not plan:
        logger.info("plan: active not found user_id=%s", current_user_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active plan found")
    logger.debug(
        "plan: active hit plan_id=%s user_id=%s",
        plan.plan_id,
        current_user_id,
    )
    return plan_to_response(plan)


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan_endpoint(
    plan_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PlanResponse:
    plan = get_plan_by_id(db, plan_id)
    if not plan or plan.user_id != current_user_id:
        logger.info(
            "plan: get denied or missing plan_id=%s user_id=%s",
            plan_id,
            current_user_id,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan_to_response(plan)
