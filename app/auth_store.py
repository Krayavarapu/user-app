from __future__ import annotations

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_session_by_token: Dict[str, str] = {}


def _token_prefix(token: str, n: int = 8) -> str:
    if not token:
        return "(empty)"
    return f"{token[:n]}…" if len(token) > n else token


def save_session(token: str, user_id: str) -> None:
    _session_by_token[token] = user_id
    logger.info(
        "session: stored user_id=%s active_sessions=%s token_prefix=%s",
        user_id,
        len(_session_by_token),
        _token_prefix(token),
    )


def get_user_id_for_token(token: str) -> Optional[str]:
    uid = _session_by_token.get(token)
    if uid is None and token:
        logger.debug("session: lookup miss token_prefix=%s", _token_prefix(token))
    return uid
