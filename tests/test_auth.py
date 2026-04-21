from __future__ import annotations

from datetime import date, timedelta
from typing import Dict

from app.database import get_db
from app.main import app
from app.models.user import User

def valid_signup_payload(user_id: str = "auth-001") -> Dict[str, object]:
    return {
        "user_id": user_id,
        "first_name": "Alex",
        "last_name": "Rivera",
        "height": "70.00",
        "weight_lbs": "160.00",
        "date_of_birth": "1995-01-10",
        "gender": "Male",
        "password": "StrongPass1!",
    }


def test_signup_then_login_success(client) -> None:
    signup_res = client.post("/auth/signup", json=valid_signup_payload())
    assert signup_res.status_code == 201
    assert signup_res.json()["user_id"] == "auth-001"

    login_res = client.post(
        "/auth/login",
        json={"username": "auth-001", "password": "StrongPass1!"},
    )
    assert login_res.status_code == 200
    body = login_res.json()
    assert body["session_token"]
    assert body["user_id"] == "auth-001"
    assert body["holds"] == []
    assert body["restrictions"] == []


def test_login_failure_is_generic_401(client) -> None:
    missing_user_login = client.post(
        "/auth/login",
        json={"username": "missing-user", "password": "WrongPass1!"},
    )
    assert missing_user_login.status_code == 401
    assert missing_user_login.json()["detail"] == "Unauthorized"

    client.post("/auth/signup", json=valid_signup_payload(user_id="auth-002"))
    wrong_password_login = client.post(
        "/auth/login",
        json={"username": "auth-002", "password": "InvalidPass1!"},
    )
    assert wrong_password_login.status_code == 401
    assert wrong_password_login.json()["detail"] == "Unauthorized"


def test_signup_validation_failures(client) -> None:
    bad_password_payload = valid_signup_payload(user_id="auth-003")
    bad_password_payload["password"] = "weakpass"
    bad_password_res = client.post("/auth/signup", json=bad_password_payload)
    assert bad_password_res.status_code == 422

    future_dob_payload = valid_signup_payload(user_id="auth-004")
    future_dob_payload["date_of_birth"] = str(date.today() + timedelta(days=1))
    future_dob_res = client.post("/auth/signup", json=future_dob_payload)
    assert future_dob_res.status_code == 422


def test_restricted_account_blocks_login(client) -> None:
    signup_payload = valid_signup_payload(user_id="auth-005")
    client.post("/auth/signup", json=signup_payload)
    override_get_db = app.dependency_overrides[get_db]
    db = next(override_get_db())
    try:
        user = db.query(User).filter(User.user_id == "auth-005").first()
        assert user is not None
        user.restrictions = "account_review"
        db.add(user)
        db.commit()
    finally:
        db.close()

    login_res = client.post(
        "/auth/login",
        json={"username": "auth-005", "password": "StrongPass1!"},
    )
    assert login_res.status_code == 401
    assert login_res.json()["detail"] == "Unauthorized"
