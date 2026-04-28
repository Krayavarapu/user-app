from __future__ import annotations


def _auth_header(client, user_id: str = "plan-user-001") -> dict:
    signup_payload = {
        "user_id": user_id,
        "first_name": "Taylor",
        "last_name": "Reed",
        "height": "68.00",
        "weight_lbs": "150.00",
        "date_of_birth": "1998-08-10",
        "gender": "Female",
        "password": "StrongPass1!",
    }
    client.post("/auth/signup", json=signup_payload)
    login_response = client.post("/auth/login", json={"username": user_id, "password": "StrongPass1!"})
    token = login_response.json()["session_token"]
    return {"Authorization": f"Bearer {token}"}


def test_generate_plan_success(client) -> None:
    headers = _auth_header(client)
    payload = {
        "prompt": "Need a beginner routine with short sessions.",
        "goal": "Build consistency",
        "equipment": "Dumbbells and yoga mat",
    }

    response = client.post("/plan/generate", json=payload, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["plan_id"]
    assert body["title"]
    assert body["summary"]
    assert len(body["workouts"]) > 0
    assert body["generated_at"]


def test_regenerate_plan_success(client) -> None:
    headers = _auth_header(client, user_id="plan-user-002")
    payload = {
        "prompt": "Need low-impact training.",
        "goal": "Improve endurance",
        "equipment": "Resistance bands only",
        "previous_plan_id": "plan-old-001",
    }

    response = client.post("/plan/regenerate", json=payload, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["plan_id"]
    assert body["notes"] == "Regenerated with updated preferences."


def test_generate_plan_requires_auth(client) -> None:
    payload = {
        "prompt": "Help me get stronger",
        "goal": "Build strength",
        "equipment": "Barbell",
    }
    response = client.post("/plan/generate", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"
