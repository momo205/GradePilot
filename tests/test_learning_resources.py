from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from _pytest.monkeypatch import MonkeyPatch
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.db.session import get_db
from app.deps.auth import CurrentUser, get_current_user
from app.main import app
from app.schemas import LearningResourceItem


@pytest.fixture()
def lr_client(
    monkeypatch: MonkeyPatch,
) -> Generator[tuple[TestClient, str], None, None]:
    engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    user_uuid = uuid.uuid4()

    def _override_get_db() -> Generator[Session, None, None]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def _override_get_current_user() -> CurrentUser:
        return CurrentUser(user_id=str(user_uuid), claims={"sub": str(user_uuid)})

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    client = TestClient(app)
    resp = client.post("/classes", json={"title": "CS 101"})
    assert resp.status_code == 200
    class_id = resp.json()["id"]

    yield client, class_id

    app.dependency_overrides.clear()


def _five_items() -> list[LearningResourceItem]:
    base = [
        ("Python lists tutorial", "youtube", "python lists explained"),
        ("Official Python docs", "web", "python list documentation site:docs.python.org"),
        ("Big-O basics video", "youtube", "big o notation computer science"),
        ("MIT OCW algorithms", "web", "MIT introduction algorithms reading"),
        ("Recursion walkthrough", "youtube", "recursion programming tutorial"),
    ]
    return [
        LearningResourceItem(
            title=t,
            rationale="Grounded in your notes on data structures.",
            destination=d,
            search_query=q,
        )
        for t, d, q in base
    ]


def test_learning_resources_ok(
    lr_client: tuple[TestClient, str], monkeypatch: MonkeyPatch
) -> None:
    client, class_id = lr_client
    n = client.post(
        f"/classes/{class_id}/notes",
        json={"notes_text": "Lists are ordered sequences."},
    )
    assert n.status_code == 200
    items = _five_items()

    def _fake_gen(**_: object) -> tuple[list[LearningResourceItem], str]:
        return items, "gemini-test"

    monkeypatch.setattr(
        "app.routers.classes.generate_learning_resources",
        _fake_gen,
    )
    resp = client.post(f"/classes/{class_id}/learning-resources")
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "gemini-test"
    assert len(data["items"]) == 5
    assert data["items"][0]["title"] == "Python lists tutorial"
    assert data["items"][0]["destination"] == "youtube"
    assert "search_query" in data["items"][0]


def test_learning_resources_no_notes(lr_client: tuple[TestClient, str]) -> None:
    client, class_id = lr_client
    resp = client.post(f"/classes/{class_id}/learning-resources")
    assert resp.status_code == 400
    assert "notes" in resp.json()["detail"].lower()
