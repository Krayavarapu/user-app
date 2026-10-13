from __future__ import annotations

from datetime import date

import pytest

from app.crud.profile import get_equipment_ids, get_profile, save_profile
from app.database import get_db
from app.main import app
from app.models.equipment import Equipment, UserEquipment
from app.models.user_profile import UserProfile
from app.schemas.profile import ProfileUpdate
from app.services.exercise_library.seed import seed_equipment

SIGNUP = {
    "first_name": "Sam",
    "last_name": "Lee",
    "height": "70.00",
    "weight_lbs": "170.00",
    "date_of_birth": "1992-03-04",
    "gender": "Male",
    "password": "StrongPass1!",
}


def auth_header(client, user_id="prof-user-001") -> dict:
    client.post("/auth/signup", json={**SIGNUP, "user_id": user_id})
    token = client.post("/auth/login", json={"username": user_id, "password": "StrongPass1!"}).json()[
        "session_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def open_test_db():
    return next(app.dependency_overrides[get_db]())


@pytest.fixture()
def seeded(client):
    db = open_test_db()
    try:
        seed_equipment(db)
    finally:
        db.close()


def body(**overrides) -> dict:
    base = {
        "experience_level": "intermediate",
        "primary_goal": "strength",
        "days_per_week": 4,
        "session_length_minutes": 60,
        "limitations": [{"code": "shoulder", "severity": "moderate"}],
        "equipment_ids": ["dumbbell", "flat_bench"],
    }
    base.update(overrides)
    return base


# --- auth ----------------------------------------------------------------------------------------


def test_profile_requires_auth(client) -> None:
    assert client.get("/users/me/profile").status_code == 401
    assert client.put("/users/me/profile", json=body()).status_code == 401


# --- defaults ------------------------------------------------------------------------------------


def test_get_without_a_saved_profile_returns_conservative_defaults(client, seeded) -> None:
    response = client.get("/users/me/profile", headers=auth_header(client))
    assert response.status_code == 200
    assert response.json() == {
        "experience_level": "beginner",
        "primary_goal": None,
        "days_per_week": 3,
        "session_length_minutes": 45,
        "limitations": [],
        "equipment_ids": [],
        "is_default": True,
        "updated_at": None,
    }


def test_get_does_not_create_a_row(client, seeded) -> None:
    client.get("/users/me/profile", headers=auth_header(client))
    db = open_test_db()
    try:
        assert db.query(UserProfile).count() == 0
    finally:
        db.close()


# --- save and read back --------------------------------------------------------------------------


def test_put_then_get_round_trips(client, seeded) -> None:
    headers = auth_header(client)
    put = client.put("/users/me/profile", json=body(), headers=headers)
    assert put.status_code == 200, put.text

    data = client.get("/users/me/profile", headers=headers).json()
    assert data["is_default"] is False
    assert data["experience_level"] == "intermediate"
    assert data["primary_goal"] == "strength"
    assert data["days_per_week"] == 4
    assert data["session_length_minutes"] == 60
    assert data["limitations"] == [{"code": "shoulder", "severity": "moderate", "notes": None}]
    assert data["equipment_ids"] == ["dumbbell", "flat_bench"]
    assert data["updated_at"]
    assert put.json() == data


def test_put_replaces_everything_including_equipment(client, seeded) -> None:
    headers = auth_header(client)
    client.put("/users/me/profile", json=body(), headers=headers)

    second = body(
        experience_level="beginner",
        primary_goal=None,
        limitations=[{"code": "knee", "severity": "severe"}],
        equipment_ids=["kettlebell"],
    )
    client.put("/users/me/profile", json=second, headers=headers)

    data = client.get("/users/me/profile", headers=headers).json()
    assert data["equipment_ids"] == ["kettlebell"]
    assert [item["code"] for item in data["limitations"]] == ["knee"]
    assert data["primary_goal"] is None
    db = open_test_db()
    try:
        assert db.query(UserProfile).count() == 1
        assert [r.equipment_id for r in db.query(UserEquipment).all()] == ["kettlebell"]
    finally:
        db.close()


def test_empty_lists_clear_limitations_and_equipment(client, seeded) -> None:
    headers = auth_header(client)
    client.put("/users/me/profile", json=body(), headers=headers)
    client.put("/users/me/profile", json=body(limitations=[], equipment_ids=[]), headers=headers)
    data = client.get("/users/me/profile", headers=headers).json()
    assert data["limitations"] == [] and data["equipment_ids"] == []
    assert data["is_default"] is False


def test_severity_defaults_to_moderate_and_notes_are_trimmed(client, seeded) -> None:
    headers = auth_header(client)
    payload = body(limitations=[{"code": "Wrist ".strip().upper()}, {"code": "knee", "notes": "  old injury  "}])
    response = client.put("/users/me/profile", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    by_code = {item["code"]: item for item in response.json()["limitations"]}
    assert by_code["wrist"]["severity"] == "moderate"
    assert by_code["knee"]["notes"] == "old injury"


def test_blank_notes_become_null(client, seeded) -> None:
    response = client.put(
        "/users/me/profile",
        json=body(limitations=[{"code": "knee", "notes": "   "}]),
        headers=auth_header(client),
    )
    assert response.json()["limitations"][0]["notes"] is None


def test_equipment_ids_are_normalised_and_deduplicated(client, seeded) -> None:
    response = client.put(
        "/users/me/profile",
        json=body(equipment_ids=[" Dumbbell ", "dumbbell", "KETTLEBELL"]),
        headers=auth_header(client),
    )
    assert response.status_code == 200, response.text
    assert response.json()["equipment_ids"] == ["dumbbell", "kettlebell"]


def test_limitations_are_returned_in_a_stable_order(client, seeded) -> None:
    payload = body(limitations=[{"code": "wrist"}, {"code": "ankle"}, {"code": "knee"}])
    response = client.put("/users/me/profile", json=payload, headers=auth_header(client))
    assert [item["code"] for item in response.json()["limitations"]] == ["ankle", "knee", "wrist"]


# --- validation ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"limitations": [{"code": "elbow", "severity": "mild"}]},
        {"limitations": [{"code": "knee", "severity": "extreme"}]},
        {"limitations": [{"code": "knee"}, {"code": "knee", "severity": "severe"}]},
        {"limitations": [{"code": "knee", "notes": "x" * 201}]},
        {"limitations": [{"code": "knee"}] * 11},
        {"experience_level": "expert"},
        {"primary_goal": "get_huge"},
        {"days_per_week": 0},
        {"days_per_week": 8},
        {"session_length_minutes": 14},
        {"session_length_minutes": 121},
        {"equipment_ids": [""]},
        {"equipment_ids": [123]},
        {"equipment_ids": ["a"] * 41},
    ],
)
def test_invalid_values_are_rejected_with_422(client, seeded, overrides) -> None:
    response = client.put("/users/me/profile", json=body(**overrides), headers=auth_header(client))
    assert response.status_code == 422, (overrides, response.text)


def test_unknown_limitation_code_lists_the_allowed_ones(client, seeded) -> None:
    response = client.put(
        "/users/me/profile", json=body(limitations=[{"code": "elbow"}]), headers=auth_header(client)
    )
    assert "allowed: ankle, hip, knee, lower_back, neck, shoulder, wrist" in response.text


@pytest.mark.parametrize("missing", ["limitations", "equipment_ids"])
def test_safety_lists_must_be_sent_explicitly(client, seeded, missing) -> None:
    """Omitting them must never silently erase saved limitations or equipment."""
    payload = body()
    del payload[missing]
    response = client.put("/users/me/profile", json=payload, headers=auth_header(client))
    assert response.status_code == 422


def test_unknown_fields_are_rejected_instead_of_dropped(client, seeded) -> None:
    payload = body()
    payload["limitation"] = [{"code": "knee", "severity": "severe"}]  # typo of "limitations"
    assert client.put("/users/me/profile", json=payload, headers=auth_header(client)).status_code == 422


def test_unknown_equipment_ids_are_rejected_with_a_helpful_message(client, seeded) -> None:
    response = client.put(
        "/users/me/profile", json=body(equipment_ids=["dumbbell", "bosu_ball", "zip_line"]), headers=auth_header(client)
    )
    assert response.status_code == 422
    assert "bosu_ball, zip_line" in response.json()["detail"]
    assert "dumbbell" not in response.json()["detail"].split(":", 1)[1]


def test_rejected_save_changes_nothing(client, seeded) -> None:
    headers = auth_header(client)
    client.put("/users/me/profile", json=body(), headers=headers)
    before = client.get("/users/me/profile", headers=headers).json()

    assert client.put("/users/me/profile", json=body(equipment_ids=["nope"]), headers=headers).status_code == 422
    assert client.put("/users/me/profile", json=body(days_per_week=9), headers=headers).status_code == 422

    assert client.get("/users/me/profile", headers=headers).json() == before


def test_deactivated_equipment_cannot_be_saved_and_is_hidden_on_read(client, seeded) -> None:
    headers = auth_header(client)
    client.put("/users/me/profile", json=body(equipment_ids=["dumbbell", "kettlebell"]), headers=headers)

    db = open_test_db()
    try:
        db.query(Equipment).filter_by(equipment_id="kettlebell").update({"is_active": False})
        db.commit()
    finally:
        db.close()

    assert client.get("/users/me/profile", headers=headers).json()["equipment_ids"] == ["dumbbell"]
    assert client.put("/users/me/profile", json=body(equipment_ids=["kettlebell"]), headers=headers).status_code == 422


# --- isolation -----------------------------------------------------------------------------------


def test_users_only_ever_see_their_own_profile(client, seeded) -> None:
    alice = auth_header(client, "alice-001")
    bob = auth_header(client, "bob-0001")
    client.put("/users/me/profile", json=body(limitations=[{"code": "knee", "severity": "severe"}]), headers=alice)

    bobs = client.get("/users/me/profile", headers=bob).json()
    assert bobs["is_default"] is True and bobs["limitations"] == [] and bobs["equipment_ids"] == []

    client.put("/users/me/profile", json=body(limitations=[], equipment_ids=["barbell"]), headers=bob)
    alices = client.get("/users/me/profile", headers=alice).json()
    assert [item["code"] for item in alices["limitations"]] == ["knee"]
    assert alices["equipment_ids"] == ["dumbbell", "flat_bench"]


def test_profile_route_does_not_shadow_user_routes(client, seeded) -> None:
    headers = auth_header(client)
    assert client.get("/users/me", headers=headers).json()["user_id"] == "prof-user-001"
    assert client.get("/users/prof-user-001", headers=headers).status_code == 200


# --- atomicity -----------------------------------------------------------------------------------


def test_a_failure_part_way_through_a_save_rolls_everything_back(db_session, monkeypatch) -> None:
    from app.models.user import User

    seed_equipment(db_session)
    db_session.add(
        User(
            user_id="atomic-user", first_name="A", last_name="B", height=70, weight_lbs=150,
            date_of_birth=date(1990, 1, 1), gender="x", created_by=date(2026, 1, 1), password_hash="x",
        )
    )
    db_session.commit()
    first = ProfileUpdate.parse_obj(body())
    save_profile(db_session, "atomic-user", first)

    second = ProfileUpdate.parse_obj(
        body(experience_level="advanced", limitations=[{"code": "hip", "severity": "severe"}], equipment_ids=["barbell"])
    )

    def boom():
        # Fail at commit time, after the changes have already been sent to the database, so only a
        # real rollback can undo them.
        db_session.flush()
        raise RuntimeError("database went away")

    monkeypatch.setattr(db_session, "commit", boom)
    with pytest.raises(RuntimeError):
        save_profile(db_session, "atomic-user", second)
    monkeypatch.undo()

    db_session.expire_all()
    profile = get_profile(db_session, "atomic-user")
    assert profile.experience_level == "intermediate"
    assert [item["code"] for item in profile.limitations] == ["shoulder"]
    assert get_equipment_ids(db_session, "atomic-user") == ["dumbbell", "flat_bench"]


# --- account deletion ----------------------------------------------------------------------------


def test_deleting_a_user_removes_their_profile_and_equipment(client, seeded) -> None:
    headers = auth_header(client, "leaver-01")
    client.put("/users/me/profile", json=body(), headers=headers)

    assert client.delete("/users/leaver-01", headers=headers).status_code == 204

    db = open_test_db()
    try:
        assert db.query(UserProfile).filter_by(user_id="leaver-01").count() == 0
        assert db.query(UserEquipment).filter_by(user_id="leaver-01").count() == 0
    finally:
        db.close()


def test_deleting_one_user_leaves_other_profiles_alone(client, seeded) -> None:
    keeper = auth_header(client, "keeper-01")
    leaver = auth_header(client, "leaver-02")
    client.put("/users/me/profile", json=body(), headers=keeper)
    client.put("/users/me/profile", json=body(), headers=leaver)

    client.delete("/users/leaver-02", headers=leaver)

    data = client.get("/users/me/profile", headers=keeper).json()
    assert data["is_default"] is False and data["equipment_ids"] == ["dumbbell", "flat_bench"]


# --- contracts that must not change --------------------------------------------------------------


def test_existing_user_and_auth_contracts_are_unchanged(client, seeded) -> None:
    headers = auth_header(client)
    me = client.get("/users/me", headers=headers).json()
    assert set(me) >= {"user_id", "first_name", "last_name", "height", "weight_lbs", "date_of_birth", "gender"}
    assert not {"limitations", "equipment_ids", "experience_level"} & set(me)
