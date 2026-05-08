from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.models.user_session import UserSession

logger = logging.getLogger(__name__)


def create_session(db: Session, token: str, user_id: str, expires_at: datetime) -> UserSession:
    session = UserSession(token=token, user_id=user_id, expires_at=expires_at)
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.debug("crud.session: created session for user_id=%s", user_id)
    return session


def get_valid_user_id_for_token(db: Session, token: str) -> Optional[str]:
    record = (
        db.query(UserSession)
        .filter(and_(UserSession.token == token, UserSession.expires_at > func.now()))
        .first()
    )
    if not record:
        return None
    return record.user_id
