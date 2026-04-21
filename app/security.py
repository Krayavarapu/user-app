from __future__ import annotations

import hashlib
import hmac
import secrets


def hash_password(password: str, *, salt: str | None = None) -> str:
    salt_value = salt or secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt_value}{password}".encode("utf-8")).hexdigest()
    return f"{salt_value}${digest}"


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        salt, _ = hashed_password.split("$", maxsplit=1)
    except ValueError:
        return False
    expected = hash_password(password, salt=salt)
    return hmac.compare_digest(expected, hashed_password)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)
