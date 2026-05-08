from __future__ import annotations

import logging
from datetime import date
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.session import create_session
from app.crud.user import create_user, get_user
from app.database import get_db
from app.schemas.auth import LoginRequest, LoginResponse, SignupRequest, SignupResponse
from app.schemas.user import UserCreate
from app.security import generate_session_token, hash_password, verify_password
from app.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _split_flags(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup_endpoint(payload: SignupRequest, db: Session = Depends(get_db)) -> SignupResponse:
    if get_user(db, payload.user_id):
        logger.warning("auth: signup conflict user_id=%s", payload.user_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with user_id '{payload.user_id}' already exists",
        )

    user_payload = UserCreate(
        first_name=payload.first_name,
        last_name=payload.last_name,
        height=payload.height,
        weight_lbs=payload.weight_lbs,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        created_by=date.today(),
        user_id=payload.user_id,
    )
    create_user(db, user_payload, password_hash=hash_password(payload.password))
    logger.info("auth: signup ok user_id=%s", payload.user_id)
    return SignupResponse(user_id=payload.user_id)


@router.post("/login", response_model=LoginResponse)
def login_endpoint(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = get_user(db, payload.username)
    if not user or not verify_password(payload.password, user.password_hash):
        logger.warning("auth: login failed (invalid credentials)")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    holds = _split_flags(user.holds)
    restrictions = _split_flags(user.restrictions)
    if holds or restrictions:
        logger.warning(
            "auth: login blocked by holds/restrictions user_id=%s holds=%s restrictions=%s",
            user.user_id,
            holds,
            restrictions,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    session_token = generate_session_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.session_ttl_days)
    create_session(db, session_token, user.user_id, expires_at)
    logger.info("auth: login ok user_id=%s", user.user_id)
    return LoginResponse(session_token=session_token, user_id=user.user_id, holds=[], restrictions=[])
