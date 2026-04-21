from __future__ import annotations

from typing import List

from fastapi import Header, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, status

from app.crud.user import create_user, delete_user, get_user, list_users, update_user
from app.database import get_db
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.auth_store import get_user_id_for_token


router = APIRouter(prefix="/users", tags=["users"])


def get_current_user_id(authorization: str = Header(default="")) -> str:
    token = authorization.replace("Bearer ", "", 1).strip()
    user_id = get_user_id_for_token(token)
    if not token or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user_id


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    if get_user(db, payload.user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with user_id '{payload.user_id}' already exists",
        )

    try:
        return create_user(db, payload)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Could not create user") from exc


@router.get("", response_model=List[UserRead])
def list_users_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> List[UserRead]:
    return list_users(db, skip=skip, limit=limit)


@router.put("/me", response_model=UserRead)
def update_me_endpoint(
    payload: UserUpdate,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> UserRead:
    existing = get_user(db, current_user_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with user_id '{current_user_id}' was not found",
        )
    return update_user(db, existing, payload)


@router.get("/{user_id}", response_model=UserRead)
def get_user_endpoint(user_id: str, db: Session = Depends(get_db)) -> UserRead:
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with user_id '{user_id}' was not found",
        )
    return user


@router.put("/{user_id}", response_model=UserRead)
def update_user_endpoint(user_id: str, payload: UserUpdate, db: Session = Depends(get_db)) -> UserRead:
    existing = get_user(db, user_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with user_id '{user_id}' was not found",
        )
    return update_user(db, existing, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_endpoint(user_id: str, db: Session = Depends(get_db)) -> Response:
    existing = get_user(db, user_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with user_id '{user_id}' was not found",
        )
    delete_user(db, existing)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
