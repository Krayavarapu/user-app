from __future__ import annotations

from typing import Dict, Optional


_session_by_token: Dict[str, str] = {}


def save_session(token: str, user_id: str) -> None:
    _session_by_token[token] = user_id


def get_user_id_for_token(token: str) -> Optional[str]:
    return _session_by_token.get(token)
