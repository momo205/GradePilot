from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.db.session import get_db
from app.main import app


def _auth(monkeypatch, *, user_id: str) -> None:  # type: ignore[no-untyped-def]
    def _fake_verify(_: str) -> dict[str, object]:
        return {"sub": user_id, "role": "authenticated"}

    monkeypatch.setattr("app.deps.auth.verify_supabase_jwt", _fake_verify)


def _override_db(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    def _get_db():  # type: ignore[no-untyped-def]
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db


def test_chat_session_materials_first_welcome(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    user_id = str(uuid.uuid4())
    _auth(monkeypatch, user_id=user_id)
    _override_db(monkeypatch)

    client = TestClient(app)
    sess = client.post("/chat/sessions", headers={"Authorization": "Bearer test"})
    assert sess.status_code == 200
    session_id = sess.json()["id"]

    loaded = client.get(
        f"/chat/sessions/{session_id}", headers={"Authorization": "Bearer test"}
    )
    assert loaded.status_code == 200
    body = loaded.json()
    # Single-class wizard uses numeric phases 1–5 (see onboarding_gate).
    assert body["state"].get("phase") == 1
    msgs = body["messages"]
    assert len(msgs) >= 1
    assert msgs[0]["role"] == "assistant"
    low = msgs[0]["content"].lower()
    assert "welcome" in low or "class" in low

    # Nudge: still prompts for class title JSON
    r1 = client.post(
        f"/chat/sessions/{session_id}/messages",
        headers={"Authorization": "Bearer test"},
        json={"content": "hi"},
    )
    assert r1.status_code == 200
    last = r1.json()["messages"][-1]["content"].lower()
    assert "class_title" in last or "json" in last


def test_chat_semester_then_classes_then_create(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    user_id = str(uuid.uuid4())
    _auth(monkeypatch, user_id=user_id)
    _override_db(monkeypatch)

    client = TestClient(app)
    sess = client.post("/chat/sessions", headers={"Authorization": "Bearer test"})
    session_id = sess.json()["id"]

    r1 = client.post(
        f"/chat/sessions/{session_id}/messages",
        headers={"Authorization": "Bearer test"},
        json={"content": '{"class_title":"CS101"}'},
    )
    assert r1.status_code == 200
    assert any(
        a.get("type") == "create_class" for a in r1.json().get("tool_actions", [])
    )
    assert r1.json()["state"].get("phase") == 2

    r2 = client.post(
        f"/chat/sessions/{session_id}/messages",
        headers={"Authorization": "Bearer test"},
        json={"content": "timezone=America/New_York; start=2026-09-01; end=2026-12-15"},
    )
    assert r2.status_code == 200
    assert any(
        a.get("type") == "set_class_timeline" for a in r2.json().get("tool_actions", [])
    )
    assert r2.json()["state"].get("phase") == 3
    low = r2.json()["messages"][-1]["content"].lower()
    assert "syllabus" in low or "deadline" in low


def test_chat_classes_first_creates_workspaces(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    user_id = str(uuid.uuid4())
    _auth(monkeypatch, user_id=user_id)
    _override_db(monkeypatch)

    client = TestClient(app)
    sess = client.post("/chat/sessions", headers={"Authorization": "Bearer test"})
    session_id = sess.json()["id"]

    r = client.post(
        f"/chat/sessions/{session_id}/messages",
        headers={"Authorization": "Bearer test"},
        json={"content": '{"class_title":"CS101"}'},
    )
    assert r.status_code == 200
    assert any(
        a.get("type") == "create_class" for a in r.json().get("tool_actions", [])
    )
    assert r.json()["state"].get("phase") == 2
