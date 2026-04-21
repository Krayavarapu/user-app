from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth_store import save_session
from app.crud.user import create_user, get_user
from app.database import get_db
from app.schemas.auth import LoginRequest, LoginResponse, SignupRequest, SignupResponse
from app.schemas.user import UserCreate
from app.security import generate_session_token, hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])


def _split_flags(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup_endpoint(payload: SignupRequest, db: Session = Depends(get_db)) -> SignupResponse:
    if get_user(db, payload.user_id):
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
    return SignupResponse(user_id=payload.user_id)


@router.post("/login", response_model=LoginResponse)
def login_endpoint(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = get_user(db, payload.username)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    holds = _split_flags(user.holds)
    restrictions = _split_flags(user.restrictions)
    if holds or restrictions:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    session_token = generate_session_token()
    save_session(session_token, user.user_id)
    return LoginResponse(session_token=session_token, user_id=user.user_id, holds=[], restrictions=[])
