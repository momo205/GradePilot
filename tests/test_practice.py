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
from app.schemas import PracticeQuestion


@pytest.fixture()
def practice_client(
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


def test_generate_practice_ok(
    practice_client: tuple[TestClient, str], monkeypatch: MonkeyPatch
) -> None:
    client, class_id = practice_client
    n = client.post(
        f"/classes/{class_id}/notes",
        json={"notes_text": "Lists are ordered sequences."},
    )
    assert n.status_code == 200
    monkeypatch.setattr(
        "app.routers.classes.generate_practice_questions",
        lambda **_: [
            PracticeQuestion(
                q="What is a list?",
                a="An ordered sequence.",
                source_label="Lecture 1",
            )
        ],
    )
    resp = client.post(
        f"/classes/{class_id}/practice",
        json={"count": 1, "difficulty": "Easy"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["questions"]) == 1
    assert body["questions"][0]["q"] == "What is a list?"
    assert body["questions"][0]["a"] == "An ordered sequence."
    assert body["questions"][0]["source_label"] == "Lecture 1"


def test_generate_practice_class_not_found(
    practice_client: tuple[TestClient, str], monkeypatch: MonkeyPatch
) -> None:
    client, _ = practice_client
    monkeypatch.setattr(
        "app.routers.classes.generate_practice_questions",
        lambda **_: [],
    )
    resp = client.post(
        f"/classes/{uuid.uuid4()}/practice",
        json={"count": 3, "difficulty": "Hard"},
    )
    assert resp.status_code == 404


def test_generate_practice_ai_error(
    practice_client: tuple[TestClient, str], monkeypatch: MonkeyPatch
) -> None:
    from app.services.practice import PracticeGenerationError

    client, class_id = practice_client
    n = client.post(
        f"/classes/{class_id}/notes",
        json={"notes_text": "Binary trees."},
    )
    assert n.status_code == 200

    def _fail(**_: object) -> list[PracticeQuestion]:
        raise PracticeGenerationError("Model unavailable")

    monkeypatch.setattr("app.routers.classes.generate_practice_questions", _fail)
    resp = client.post(
        f"/classes/{class_id}/practice",
        json={"count": 5, "difficulty": "Medium"},
    )
    assert resp.status_code == 502
    assert "Model unavailable" in resp.json()["detail"]


def test_generate_practice_no_notes(
    practice_client: tuple[TestClient, str],
) -> None:
    client, class_id = practice_client
    resp = client.post(
        f"/classes/{class_id}/practice",
        json={"count": 3, "difficulty": "Easy"},
    )
    assert resp.status_code == 400
    assert "notes" in resp.json()["detail"].lower()


def test_generate_practice_invalid_difficulty(
    practice_client: tuple[TestClient, str],
) -> None:
    client, class_id = practice_client
    n = client.post(
        f"/classes/{class_id}/notes",
        json={"notes_text": "Sorting algorithms."},
    )
    assert n.status_code == 200
    resp = client.post(
        f"/classes/{class_id}/practice",
        json={"count": 3, "difficulty": "banana"},
    )
    assert resp.status_code == 422
