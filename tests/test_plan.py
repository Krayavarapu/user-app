from __future__ import annotations

import pytest

from app.database import get_db
from app.main import app
from app.models.fitness_plan import FitnessPlan


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
        "duration_days": 7,
    }

    response = client.post("/plan/generate", json=payload, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["plan_id"]
    assert body["title"]
    assert body["summary"]
    assert body["duration_days"] == 7
    assert len(body["days"]) == 7
    assert body["days"][0]["day_number"] == 1
    assert body["generated_at"]


def test_regenerate_plan_success(client) -> None:
    headers = _auth_header(client, user_id="plan-user-002")
    first_res = client.post(
        "/plan/generate",
        json={"prompt": "initial", "goal": "Improve endurance", "equipment": "Bands", "duration_days": 5},
        headers=headers,
    )
    payload = {
        "prompt": "Need low-impact training.",
        "goal": "Improve endurance",
        "equipment": "Resistance bands only",
        "duration_days": 5,
        "previous_plan_id": first_res.json()["plan_id"],
    }

    response = client.post("/plan/regenerate", json=payload, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["plan_id"]
    assert len(body["days"]) == 5
    assert "regenerated with updated preferences." in (body["notes"] or "").lower()


def test_generate_plan_requires_auth(client) -> None:
    payload = {
        "prompt": "Help me get stronger",
        "goal": "Build strength",
        "equipment": "Barbell",
        "duration_days": 3,
    }
    response = client.post("/plan/generate", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"


def test_get_active_plan_success(client) -> None:
    headers = _auth_header(client, user_id="plan-user-003")
    payload = {
        "prompt": "Need efficient workouts.",
        "goal": "Gain muscle",
        "equipment": "Dumbbells",
        "duration_days": 4,
    }
    client.post("/plan/generate", json=payload, headers=headers)

    active_res = client.get("/plan/active", headers=headers)
    assert active_res.status_code == 200
    body = active_res.json()
    assert body["duration_days"] == 4
    assert len(body["days"]) == 4


def test_generate_plan_openai_provider_mocked_success(client, monkeypatch) -> None:
    headers = _auth_header(client, user_id="plan-user-004")

    def fake_openai_generate(self, *, user, payload, is_regeneration):
        return {
            "title": "AI Custom Plan",
            "summary": f"AI generated for {payload.goal}",
            "days": [
                {
                    "day_number": 1,
                    "day_label": "Day 1",
                    "focus": "Strength",
                    "exercises": ["Squat", "Push Up", "Plank"],
                },
                {
                    "day_number": 2,
                    "day_label": "Day 2",
                    "focus": "Conditioning",
                    "exercises": ["Jog", "Lunges", "Stretch"],
                },
            ],
            "notes": "",
        }

    monkeypatch.setattr(
        "app.services.plan_providers.openai_provider.OpenAIPlanProvider.generate",
        fake_openai_generate,
    )
    payload = {
        "prompt": "Custom prompt",
        "goal": "Get fitter",
        "equipment": "Bodyweight",
        "duration_days": 2,
    }
    response = client.post("/plan/generate", json=payload, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "AI Custom Plan"
    assert body["notes"] in (None, "")
    assert len(body["days"]) == 2


def test_generate_plan_falls_back_when_openai_fails(client, monkeypatch) -> None:
    headers = _auth_header(client, user_id="plan-user-005")

    def failing_generate(*, user, payload, is_regeneration):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        "app.services.plan_providers.openai_provider.OpenAIPlanProvider.generate",
        failing_generate,
    )
    payload = {
        "prompt": "Need fallback",
        "goal": "Lose fat",
        "equipment": "Bands",
        "duration_days": 3,
    }
    response = client.post("/plan/generate", json=payload, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "fallback provider" in (body.get("notes") or "").lower()
    assert len(body["days"]) == 3


def test_regenerate_archives_previous_active_plan(client) -> None:
    headers = _auth_header(client, user_id="plan-user-006")
    initial_payload = {
        "prompt": "first",
        "goal": "strength",
        "equipment": "dumbbells",
        "duration_days": 2,
    }
    first_res = client.post("/plan/generate", json=initial_payload, headers=headers)
    first_plan_id = first_res.json()["plan_id"]

    regen_payload = {
        "prompt": "second",
        "goal": "strength",
        "equipment": "barbell",
        "duration_days": 2,
        "previous_plan_id": first_plan_id,
    }
    second_res = client.post("/plan/regenerate", json=regen_payload, headers=headers)
    second_plan_id = second_res.json()["plan_id"]
    assert second_plan_id != first_plan_id

    override_get_db = app.dependency_overrides[get_db]
    db = next(override_get_db())
    try:
        plans = db.query(FitnessPlan).filter(FitnessPlan.user_id == "plan-user-006").all()
        statuses = {plan.plan_id: plan.status for plan in plans}
        assert statuses[first_plan_id] == "archived"
        assert statuses[second_plan_id] == "active"
    finally:
        db.close()


def test_generate_plan_missing_api_key_uses_fallback(client, monkeypatch) -> None:
    headers = _auth_header(client, user_id="plan-user-007")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    payload = {
        "prompt": "No api key configured",
        "goal": "Build endurance",
        "equipment": "Bodyweight",
        "duration_days": 2,
    }
    response = client.post("/plan/generate", json=payload, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "fallback provider" in (body.get("notes") or "").lower()


def _plan_statuses(user_id: str) -> dict:
    """Read plan statuses through a fresh session (what another request would see)."""
    db = next(app.dependency_overrides[get_db]())
    try:
        plans = db.query(FitnessPlan).filter(FitnessPlan.user_id == user_id).all()
        return {plan.plan_id: plan.status for plan in plans}
    finally:
        db.close()


def _generate(client, headers, **overrides) -> dict:
    payload = {"prompt": "p", "goal": "g", "equipment": "Dumbbells", "duration_days": 2, **overrides}
    response = client.post("/plan/generate", json=payload, headers=headers)
    assert response.status_code == 200
    return response.json()


def test_failed_generation_does_not_archive_active_plan(client, monkeypatch) -> None:
    headers = _auth_header(client, user_id="plan-user-008")
    first_plan_id = _generate(client, headers)["plan_id"]

    def failing_generate(**kwargs):
        raise RuntimeError("generation exploded")

    monkeypatch.setattr("app.api.routes.plan.generate_plan_payload", failing_generate)

    payload = {"prompt": "p", "goal": "g", "equipment": "Dumbbells", "duration_days": 2}
    with pytest.raises(RuntimeError):
        client.post("/plan/generate", json=payload, headers=headers)
    with pytest.raises(RuntimeError):
        client.post("/plan/regenerate", json={**payload, "previous_plan_id": first_plan_id}, headers=headers)

    assert _plan_statuses("plan-user-008") == {first_plan_id: "active"}
    active = client.get("/plan/active", headers=headers)
    assert active.status_code == 200
    assert active.json()["plan_id"] == first_plan_id


def test_failed_plan_persistence_rolls_back_archive(client, monkeypatch) -> None:
    headers = _auth_header(client, user_id="plan-user-009")
    first_plan_id = _generate(client, headers)["plan_id"]

    def failing_create_plan(db, **kwargs):
        raise RuntimeError("insert failed")

    monkeypatch.setattr("app.api.routes.plan.create_plan", failing_create_plan)

    payload = {"prompt": "p", "goal": "g", "equipment": "Dumbbells", "duration_days": 2}
    with pytest.raises(RuntimeError):
        client.post("/plan/generate", json=payload, headers=headers)

    assert _plan_statuses("plan-user-009") == {first_plan_id: "active"}


def test_regenerate_unknown_previous_plan_returns_404(client) -> None:
    headers = _auth_header(client, user_id="plan-user-010")
    first_plan_id = _generate(client, headers)["plan_id"]

    response = client.post(
        "/plan/regenerate",
        json={"prompt": "p", "goal": "g", "equipment": "Dumbbells", "duration_days": 2, "previous_plan_id": "plan-nope"},
        headers=headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Plan not found"
    assert _plan_statuses("plan-user-010") == {first_plan_id: "active"}


def test_regenerate_rejects_foreign_previous_plan_id(client) -> None:
    owner_headers = _auth_header(client, user_id="plan-user-011")
    other_headers = _auth_header(client, user_id="plan-user-012")
    owner_plan_id = _generate(client, owner_headers)["plan_id"]
    other_plan_id = _generate(client, other_headers)["plan_id"]

    response = client.post(
        "/plan/regenerate",
        json={
            "prompt": "p",
            "goal": "g",
            "equipment": "Dumbbells",
            "duration_days": 2,
            "previous_plan_id": owner_plan_id,
        },
        headers=other_headers,
    )
    # Same response as a missing plan, so plan IDs can't be probed.
    assert response.status_code == 404
    assert response.json()["detail"] == "Plan not found"
    assert _plan_statuses("plan-user-011") == {owner_plan_id: "active"}
    assert _plan_statuses("plan-user-012") == {other_plan_id: "active"}


def test_regenerate_without_previous_plan_id_still_works(client) -> None:
    headers = _auth_header(client, user_id="plan-user-013")
    response = client.post(
        "/plan/regenerate",
        json={"prompt": "p", "goal": "g", "equipment": "Dumbbells", "duration_days": 2},
        headers=headers,
    )
    assert response.status_code == 200
