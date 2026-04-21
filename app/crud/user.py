from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.security import hash_password


def get_user(db: Session, user_id: str) -> Optional[User]:
    return db.query(User).filter(User.user_id == user_id).first()


def list_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, payload: UserCreate, password_hash: Optional[str] = None) -> User:
    user = User(
        **payload.dict(),
        password_hash=password_hash or hash_password("temporary-password"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, existing: User, payload: UserUpdate) -> User:
    for key, value in payload.dict().items():
        setattr(existing, key, value)

    db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing


def delete_user(db: Session, existing: User) -> None:
    db.delete(existing)
    db.commit()
