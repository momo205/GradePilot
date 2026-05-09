from __future__ import annotations

import uuid
from collections.abc import Generator

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
def gb_client() -> Generator[tuple[TestClient, str], None, None]:
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
    resp = client.post("/classes", json={"title": "Stats 101"})
    assert resp.status_code == 200
    class_id = resp.json()["id"]

    yield client, class_id

    app.dependency_overrides.clear()


def test_put_grade_book_ok(gb_client: tuple[TestClient, str]) -> None:
    client, class_id = gb_client
    body = {
        "components": [
            {
                "id": "a",
                "name": "Midterm",
                "weight_percent": 30,
                "score_percent": 82,
            },
            {
                "id": "b",
                "name": "Final",
                "weight_percent": 40,
                "score_percent": None,
            },
            {
                "id": "c",
                "name": "Homework",
                "weight_percent": 30,
                "score_percent": 95,
            },
        ],
        "pass_percent": 60,
        "target_percent": 80,
    }
    r = client.put(f"/classes/{class_id}/grade-book", json=body)
    assert r.status_code == 200
    data = r.json()
    assert len(data["components"]) == 3
    assert data["components"][1]["score_percent"] is None

    s = client.get(f"/classes/{class_id}")
    assert s.status_code == 200
    gb = s.json()["clazz"]["grade_book"]
    assert gb is not None
    assert gb["target_percent"] == 80


def test_put_grade_book_weights_must_sum(gb_client: tuple[TestClient, str]) -> None:
    client, class_id = gb_client
    body = {
        "components": [
            {"id": "a", "name": "Exam", "weight_percent": 50, "score_percent": None},
            {"id": "b", "name": "Rest", "weight_percent": 40, "score_percent": None},
        ],
        "pass_percent": 60,
        "target_percent": 70,
    }
    r = client.put(f"/classes/{class_id}/grade-book", json=body)
    assert r.status_code == 422


def test_put_grade_book_empty_components_ok(gb_client: tuple[TestClient, str]) -> None:
    client, class_id = gb_client
    body = {"components": [], "pass_percent": 60, "target_percent": 70}
    r = client.put(f"/classes/{class_id}/grade-book", json=body)
    assert r.status_code == 200
    s = client.get(f"/classes/{class_id}")
    assert s.json()["clazz"]["grade_book"]["components"] == []


def test_put_grade_book_class_missing(gb_client: tuple[TestClient, str]) -> None:
    client, _ = gb_client
    body = {
        "components": [
            {"id": "a", "name": "Final", "weight_percent": 100, "score_percent": None},
        ],
        "pass_percent": 60,
        "target_percent": 70,
    }
    r = client.put(f"/classes/{uuid.uuid4()}/grade-book", json=body)
    assert r.status_code == 404
