from __future__ import annotations

import logging
from typing import List

from fastapi import Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, status

from app.crud.user import create_user, delete_user, get_user, list_users, update_user
from app.database import get_db
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.api.deps import get_current_user_id


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    if get_user(db, payload.user_id):
        logger.warning("users: create conflict user_id=%s", payload.user_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with user_id '{payload.user_id}' already exists",
        )

    try:
        user = create_user(db, payload)
        logger.info("users: created user_id=%s", user.user_id)
        return user
    except IntegrityError as exc:
        db.rollback()
        logger.warning("users: create integrity error user_id=%s", payload.user_id)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Could not create user") from exc


@router.get("", response_model=List[UserRead])
def list_users_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> List[UserRead]:
    rows = list_users(db, skip=skip, limit=limit)
    logger.debug("users: list skip=%s limit=%s count=%s", skip, limit, len(rows))
    return rows


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
    updated = update_user(db, existing, payload)
    logger.info("users: updated self user_id=%s", current_user_id)
    return updated


@router.get("/{user_id}", response_model=UserRead)
def get_user_endpoint(user_id: str, db: Session = Depends(get_db)) -> UserRead:
    user = get_user(db, user_id)
    if not user:
        logger.info("users: get not found user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with user_id '{user_id}' was not found",
        )
    return user


@router.put("/{user_id}", response_model=UserRead)
def update_user_endpoint(user_id: str, payload: UserUpdate, db: Session = Depends(get_db)) -> UserRead:
    existing = get_user(db, user_id)
    if not existing:
        logger.info("users: update not found user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with user_id '{user_id}' was not found",
        )
    updated = update_user(db, existing, payload)
    logger.info("users: updated user_id=%s", user_id)
    return updated


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_endpoint(user_id: str, db: Session = Depends(get_db)) -> Response:
    existing = get_user(db, user_id)
    if not existing:
        logger.info("users: delete not found user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with user_id '{user_id}' was not found",
        )
    delete_user(db, existing)
    logger.info("users: deleted user_id=%s", user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
