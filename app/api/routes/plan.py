from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth_store import get_user_id_for_token
from app.crud.plan import (
    archive_user_active_plans,
    create_plan,
    get_active_plan_for_user,
    get_plan_by_id,
    plan_to_response,
)
from app.crud.user import get_user
from app.database import get_db
from app.schemas.plan import PlanGenerateRequest, PlanRegenerateRequest, PlanResponse
from app.services.plan_generator import generate_plan_payload


router = APIRouter(prefix="/plan", tags=["plan"])


def get_current_user_id(authorization: str = Header(default="")) -> str:
    token = authorization.replace("Bearer ", "", 1).strip()
    user_id = get_user_id_for_token(token)
    if not token or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user_id


def get_authenticated_user(db: Session, user_id: str):
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user


@router.post("/generate", response_model=PlanResponse)
def generate_plan_endpoint(
    payload: PlanGenerateRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PlanResponse:
    user = get_authenticated_user(db, current_user_id)
    archive_user_active_plans(db, user.user_id)
    generated = generate_plan_payload(user=user, payload=payload)
    plan = create_plan(db, user_id=user.user_id, **generated)
    return plan_to_response(plan)


@router.post("/regenerate", response_model=PlanResponse)
def regenerate_plan_endpoint(
    payload: PlanRegenerateRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PlanResponse:
    user = get_authenticated_user(db, current_user_id)
    archive_user_active_plans(db, user.user_id)
    generated = generate_plan_payload(user=user, payload=payload, is_regeneration=True)
    plan = create_plan(db, user_id=user.user_id, **generated)
    return plan_to_response(plan)


@router.get("/active", response_model=PlanResponse)
def get_active_plan_endpoint(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PlanResponse:
    plan = get_active_plan_for_user(db, current_user_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active plan found")
    return plan_to_response(plan)


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan_endpoint(
    plan_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> PlanResponse:
    plan = get_plan_by_id(db, plan_id)
    if not plan or plan.user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan_to_response(plan)
