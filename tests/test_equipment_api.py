from __future__ import annotations

from app.crud.equipment import list_alias_sources
from app.database import get_db
from app.main import app
from app.models.equipment import Equipment
from app.services.exercise_library.seed import load_equipment_seed, seed_equipment
from app.services.plan_pipeline.inputs import match_free_text_equipment


def _auth_header(client, user_id: str = "equip-user-001") -> dict:
    client.post(
        "/auth/signup",
        json={
            "user_id": user_id,
            "first_name": "Sam",
            "last_name": "Lee",
            "height": "70.00",
            "weight_lbs": "170.00",
            "date_of_birth": "1992-03-04",
            "gender": "Male",
            "password": "StrongPass1!",
        },
    )
    token = client.post("/auth/login", json={"username": user_id, "password": "StrongPass1!"}).json()["session_token"]
    return {"Authorization": f"Bearer {token}"}


def _test_db():
    """A session on the same database the TestClient is using."""
    return next(app.dependency_overrides[get_db]())


def test_equipment_requires_auth(client) -> None:
    assert client.get("/equipment").status_code == 401


def test_equipment_is_empty_before_seeding(client) -> None:
    response = client.get("/equipment", headers=_auth_header(client))
    assert response.status_code == 200
    assert response.json() == []


def test_equipment_returns_seeded_catalog(client) -> None:
    db = _test_db()
    try:
        seed_equipment(db)
    finally:
        db.close()

    response = client.get("/equipment", headers=_auth_header(client))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(load_equipment_seed().equipment)

    dumbbell = next(entry for entry in body if entry["equipment_id"] == "dumbbell")
    assert dumbbell == {"equipment_id": "dumbbell", "name": "Dumbbells", "category": "free_weights"}
    # Aliases are matching internals, not part of the public contract.
    assert all(set(entry) == {"equipment_id", "name", "category"} for entry in body)


def test_equipment_is_ordered_by_category_then_name(client) -> None:
    db = _test_db()
    try:
        seed_equipment(db)
    finally:
        db.close()

    body = client.get("/equipment", headers=_auth_header(client)).json()
    keys = [(entry["category"], entry["name"]) for entry in body]
    assert keys == sorted(keys)


def test_equipment_hides_inactive_rows(client) -> None:
    db = _test_db()
    try:
        seed_equipment(db)
        db.get(Equipment, "sandbag").is_active = False
        db.commit()
    finally:
        db.close()

    body = client.get("/equipment", headers=_auth_header(client)).json()
    ids = {entry["equipment_id"] for entry in body}
    assert "sandbag" not in ids
    assert "dumbbell" in ids


# --- DB-backed free-text matching (what the pipeline will call) --------------------------------


def test_match_free_text_equipment_uses_active_catalog_rows(db_session) -> None:
    seed_equipment(db_session)

    match = match_free_text_equipment(db_session, "Dumbbells, a bench and resistance bands")
    assert match.equipment_ids == ("dumbbell", "flat_bench", "resistance_band")

    # Deactivated equipment can no longer be matched, so it can't unlock exercises.
    db_session.get(Equipment, "dumbbell").is_active = False
    db_session.commit()
    assert "dumbbell" not in {source.equipment_id for source in list_alias_sources(db_session)}
    assert match_free_text_equipment(db_session, "dumbbells").equipment_ids == ()


def test_match_free_text_equipment_with_empty_catalog_matches_nothing(db_session) -> None:
    assert match_free_text_equipment(db_session, "dumbbells").equipment_ids == ()
