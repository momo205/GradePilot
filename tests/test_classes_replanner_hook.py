from __future__ import annotations

import uuid
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.db.session import get_db
from app.deps.auth import CurrentUser, get_current_user
from app.main import app


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    user_id = uuid.uuid4()

    def _override_get_db() -> Generator[Session, None, None]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def _override_get_current_user() -> CurrentUser:
        return CurrentUser(user_id=str(user_id), claims={"sub": str(user_id)})

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_post_notes_calls_replanner_hook(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.routers.classes as classes_router

    calls: list[str] = []

    async def _spy(*, user: Any, class_id: Any, trigger: str) -> None:
        calls.append(trigger)

    monkeypatch.setattr(classes_router, "_fire_replanner_after_write", _spy)

    r = client.post("/classes", json={"title": "HookTest"})
    assert r.status_code == 200
    class_id = r.json()["id"]

    r = client.post(f"/classes/{class_id}/notes", json={"notes_text": "hello"})
    assert r.status_code == 200
    assert calls == ["notes_added"]


def test_post_deadline_calls_replanner_hook(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.routers.classes as classes_router

    calls: list[str] = []

    async def _spy(*, user: Any, class_id: Any, trigger: str) -> None:
        calls.append(trigger)

    monkeypatch.setattr(classes_router, "_fire_replanner_after_write", _spy)

    r = client.post("/classes", json={"title": "HookTest2"})
    assert r.status_code == 200
    class_id = r.json()["id"]

    r = client.post(
        f"/classes/{class_id}/deadlines",
        json={"title": "Exam", "due": "2026-12-01"},
    )
    assert r.status_code == 200
    assert calls == ["deadline_added"]
