from __future__ import annotations

from datetime import date, timedelta
from typing import Dict


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


def test_create_get_list_update_delete_user(client) -> None:
    create_res = client.post("/users", json=valid_user_payload())
    assert create_res.status_code == 201
    body = create_res.json()
    assert body["user_id"] == "u-001"

    list_res = client.get("/users")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    get_res = client.get("/users/u-001")
    assert get_res.status_code == 200
    assert get_res.json()["first_name"] == "Ada"

    update_payload = {
        "first_name": "Grace",
        "last_name": "Hopper",
        "height": "67.20",
        "weight_lbs": "135.00",
        "date_of_birth": "1988-01-01",
        "gender": "female",
        "created_by": "2026-04-20",
    }
    update_res = client.put("/users/u-001", json=update_payload)
    assert update_res.status_code == 200
    assert update_res.json()["first_name"] == "Grace"

    delete_res = client.delete("/users/u-001")
    assert delete_res.status_code == 204

    get_after_delete = client.get("/users/u-001")
    assert get_after_delete.status_code == 404


def test_duplicate_user_id_rejected(client) -> None:
    payload = valid_user_payload()
    first = client.post("/users", json=payload)
    second = client.post("/users", json=payload)
    assert first.status_code == 201
    assert second.status_code == 409


def test_not_found_read_update_delete(client) -> None:
    get_res = client.get("/users/missing")
    put_res = client.put(
        "/users/missing",
        json={
            "first_name": "X",
            "last_name": "Y",
            "height": "61.20",
            "weight_lbs": "140.00",
            "date_of_birth": "1990-01-01",
            "gender": "other",
            "created_by": "2026-04-20",
        },
    )
    delete_res = client.delete("/users/missing")

    assert get_res.status_code == 404
    assert put_res.status_code == 404
    assert delete_res.status_code == 404


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
