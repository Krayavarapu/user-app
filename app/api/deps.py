from __future__ import annotations

import logging

from fastapi import Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth_store import get_user_id_for_token
from app.crud.user import get_user
from app.models.user import User

logger = logging.getLogger(__name__)


def _token_prefix(token: str, n: int = 8) -> str:
    if not token:
        return "(empty)"
    return f"{token[:n]}…" if len(token) > n else token


def get_current_user_id(authorization: str = Header(default="")) -> str:
    token = authorization.replace("Bearer ", "", 1).strip()
    user_id = get_user_id_for_token(token)
    if not token:
        logger.warning("auth: missing bearer token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    if not user_id:
        logger.warning("auth: unknown or stale session token_prefix=%s", _token_prefix(token))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    logger.debug("auth: session resolved user_id=%s", user_id)
    return user_id


def get_authenticated_user(db: Session, user_id: str) -> User:
    user = get_user(db, user_id)
    if not user:
        logger.warning(
            "auth: valid session token but user missing in db user_id=%s",
            user_id,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user
