from __future__ import annotations

from collections.abc import Generator

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import get_db
from app.main import app
from app.models import user  # noqa: F401
from app.models import user_session  # noqa: F401
from app.models import equipment  # noqa: F401
from app.models import exercise  # noqa: F401
from app.models.base import Base


@pytest.fixture(autouse=True)
def _isolate_from_external_services(monkeypatch) -> None:
    """Keep every test offline and independent of the developer's local .env.

    app.main loads .env at import time, so a real OPENAI_API_KEY could otherwise be picked
    up by tests. Real network I/O is blocked at the httpx transport layer. FastAPI's
    TestClient uses its own in-process transport, and tests that need to exercise an HTTP
    provider can inject httpx.MockTransport, so neither is affected.
    """
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    def _blocked(self, request):  # noqa: ANN001
        raise AssertionError(f"network disabled in tests: {request.method} {request.url}")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _blocked)


@pytest.fixture(autouse=True)
def _fresh_exercise_library_cache() -> Generator[None, None, None]:
    """The library snapshot is cached per database URL; never let it leak between tests."""
    from app.services.exercise_library.repository import clear_library_cache

    clear_library_cache()
    yield
    clear_library_cache()


@pytest.fixture()
def db_session(tmp_path) -> Generator[Session, None, None]:
    """A SQLAlchemy session on a throwaway SQLite DB, for tests that don't need HTTP."""
    engine = create_engine(f"sqlite:///{tmp_path / 'db_session.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    db_path = tmp_path / "test.db"
    test_database_url = f"sqlite:///{db_path}"
    engine = create_engine(test_database_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
