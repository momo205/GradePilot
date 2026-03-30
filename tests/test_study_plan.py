from __future__ import annotations

import uuid
from collections.abc import Generator
from typing import Any

from fastapi.testclient import TestClient
from _pytest.monkeypatch import MonkeyPatch
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base
from app.db.session import get_db
from app.deps.auth import CurrentUser, get_current_user
from app.main import app


def test_notes_to_study_plan_flow(monkeypatch: MonkeyPatch) -> None:
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

    def _fake_generate_study_plan(
        *, class_title: str, notes_text: str
    ) -> tuple[dict[str, Any], str]:
        assert class_title == "Math 101"
        assert "limits" in notes_text
        return (
            {
                "title": "Math 101 plan",
                "goals": ["Understand limits"],
                "schedule": [{"day": "Day 1", "tasks": ["Review limits basics"]}],
            },
            "fake-model",
        )

    monkeypatch.setattr(
        "app.routers.classes.generate_study_plan", _fake_generate_study_plan
    )

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    client = TestClient(app)

    # Create class
    resp = client.post("/classes", json={"title": "Math 101"})
    assert resp.status_code == 200
    class_id = resp.json()["id"]

    # Add notes
    resp = client.post(
        f"/classes/{class_id}/notes",
        json={"notes_text": "Today we covered limits and continuity."},
    )
    assert resp.status_code == 200
    notes_id = resp.json()["id"]

    # Generate study plan
    resp = client.post(f"/classes/{class_id}/study-plan", json={"notes_id": notes_id})
    assert resp.status_code == 200
    plan = resp.json()
    assert plan["class_id"] == class_id
    assert plan["source_notes_id"] == notes_id
    assert plan["model"] == "fake-model"
    assert plan["plan_json"]["title"] == "Math 101 plan"

    app.dependency_overrides.clear()
