from __future__ import annotations

from datetime import date, timedelta
from typing import Dict

UPDATE_PAYLOAD = {
    "first_name": "Grace",
    "last_name": "Hopper",
    "height": "67.20",
    "weight_lbs": "135.00",
    "date_of_birth": "1988-01-01",
    "gender": "female",
    "created_by": "2026-04-20",
}


def valid_user_payload(user_id: str = "u-001") -> Dict[str, object]:
    return {
        "user_id": user_id,
        "first_name": "Ada",
        "last_name": "Lovelace",
        "height": "66.00",
        "weight_lbs": "125.00",
        "date_of_birth": "1990-12-01",
        "gender": "female",
        "created_by": "2026-04-20",
    }


def _auth_header(client, user_id: str) -> Dict[str, str]:
    client.post(
        "/auth/signup",
        json={
            "user_id": user_id,
            "first_name": "Ada",
            "last_name": "Lovelace",
            "height": "66.00",
            "weight_lbs": "125.00",
            "date_of_birth": "1990-12-01",
            "gender": "female",
            "password": "StrongPass1!",
        },
    )
    login = client.post("/auth/login", json={"username": user_id, "password": "StrongPass1!"})
    return {"Authorization": f"Bearer {login.json()['session_token']}"}


def test_create_and_list_users(client) -> None:
    create_res = client.post("/users", json=valid_user_payload())
    assert create_res.status_code == 201
    assert create_res.json()["user_id"] == "u-001"

    list_res = client.get("/users")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


def test_get_me_returns_current_user(client) -> None:
    headers = _auth_header(client, "u-me")
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "u-me"
    assert body["first_name"] == "Ada"
    assert "password_hash" not in body


def test_get_update_delete_own_user(client) -> None:
    headers = _auth_header(client, "u-self")

    get_res = client.get("/users/u-self", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["first_name"] == "Ada"

    update_res = client.put("/users/u-self", json=UPDATE_PAYLOAD, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["first_name"] == "Grace"

    delete_res = client.delete("/users/u-self", headers=headers)
    assert delete_res.status_code == 204

    # The session may or may not survive the delete depending on the DB's FK enforcement.
    assert client.get("/users/u-self", headers=headers).status_code in (401, 404)


def test_user_id_endpoints_require_auth(client) -> None:
    client.post("/auth/signup", json={**valid_user_payload("u-auth"), "password": "StrongPass1!"})

    assert client.get("/users/me").status_code == 401
    assert client.get("/users/u-auth").status_code == 401
    assert client.put("/users/u-auth", json=UPDATE_PAYLOAD).status_code == 401
    assert client.delete("/users/u-auth").status_code == 401
    assert client.get("/users/u-auth", headers={"Authorization": "Bearer not-a-real-token"}).status_code == 401


def test_cannot_read_update_or_delete_another_user(client) -> None:
    owner_headers = _auth_header(client, "u-owner")
    attacker_headers = _auth_header(client, "u-attacker")

    assert client.get("/users/u-owner", headers=attacker_headers).status_code == 404
    assert client.put("/users/u-owner", json=UPDATE_PAYLOAD, headers=attacker_headers).status_code == 404
    assert client.delete("/users/u-owner", headers=attacker_headers).status_code == 404

    # Owner is untouched.
    still_there = client.get("/users/u-owner", headers=owner_headers)
    assert still_there.status_code == 200
    assert still_there.json()["first_name"] == "Ada"


def test_other_users_and_missing_users_are_indistinguishable(client) -> None:
    _auth_header(client, "u-exists")
    headers = _auth_header(client, "u-caller")

    existing = client.get("/users/u-exists", headers=headers)
    missing = client.get("/users/u-missing", headers=headers)
    assert existing.status_code == missing.status_code == 404
    assert existing.json()["detail"].replace("u-exists", "X") == missing.json()["detail"].replace("u-missing", "X")


def test_duplicate_user_id_rejected(client) -> None:
    payload = valid_user_payload()
    first = client.post("/users", json=payload)
    second = client.post("/users", json=payload)
    assert first.status_code == 201
    assert second.status_code == 409


def test_validation_errors(client) -> None:
    bad_height_payload = valid_user_payload(user_id="u-002")
    bad_height_payload["height"] = "-1"
    bad_height_res = client.post("/users", json=bad_height_payload)
    assert bad_height_res.status_code == 422

    future_date_payload = valid_user_payload(user_id="u-003")
    future_date_payload["date_of_birth"] = str(date.today() + timedelta(days=1))
    future_date_res = client.post("/users", json=future_date_payload)
    assert future_date_res.status_code == 422

    missing_field_payload = valid_user_payload(user_id="u-004")
    del missing_field_payload["first_name"]
    missing_field_res = client.post("/users", json=missing_field_payload)
    assert missing_field_res.status_code == 422
