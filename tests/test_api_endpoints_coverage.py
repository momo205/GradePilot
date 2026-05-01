from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base
from app.db.session import get_db
from app.deps.auth import CurrentUser, get_current_user
from app.main import app


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}
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


def test_health_and_root(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["message"] == "GradePilot API"


def test_classes_create_list_and_summary(client: TestClient) -> None:
    r = client.post("/classes", json={"title": "CS101"})
    assert r.status_code == 200
    class_id = r.json()["id"]

    r = client.get("/classes")
    assert r.status_code == 200
    assert any(c["id"] == class_id for c in r.json())

    r = client.get(f"/classes/{class_id}")
    assert r.status_code == 200
    payload = r.json()
    assert payload["clazz"]["id"] == class_id
    assert payload["deadline_count"] == 0


def test_chat_session_create_get_and_post_message_creates_classes(client: TestClient) -> None:
    r = client.post("/chat/sessions")
    assert r.status_code == 200
    session_id = r.json()["id"]

    r = client.get(f"/chat/sessions/{session_id}")
    assert r.status_code == 200
    assert r.json()["session"]["id"] == session_id

    # Deterministic onboarding: comma-separated titles -> tool action create_classes
    r = client.post(
        f"/chat/sessions/{session_id}/messages",
        json={"content": "CS101, Calculus II"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["session"]["id"] == session_id
    assert any(m["role"] == "user" for m in body["messages"])
    assert any(m["role"] == "assistant" for m in body["messages"])

    # The tool action list should include create_classes
    assert any(a["type"] == "create_classes" for a in body["tool_actions"])


def test_rag_ask_returns_fallback_when_no_chunks(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    # Create class to satisfy "Class not found" check.
    r = client.post("/classes", json={"title": "History"})
    assert r.status_code == 200
    class_id = r.json()["id"]

    import app.routers.rag as rag_router

    def _fake_retrieve_chunks(*args, **kwargs):  # noqa: ANN001, D401
        return []

    monkeypatch.setattr(rag_router, "retrieve_chunks", _fake_retrieve_chunks)

    r = client.post(f"/classes/{class_id}/ask", json={"question": "What is the exam?"})
    assert r.status_code == 200
    out = r.json()
    assert out["sources"] == []
    assert "don't have enough information" in out["answer"].lower()


def test_rag_upload_material_raw_text_path(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    r = client.post("/classes", json={"title": "Biology"})
    assert r.status_code == 200
    class_id = r.json()["id"]

    import app.routers.rag as rag_router

    class _Result:
        def __init__(self) -> None:
            self.document_id = uuid.uuid4()
            self.chunks_created = 2

    def _fake_ingest_raw_text(*args, **kwargs):  # noqa: ANN001
        return _Result()

    monkeypatch.setattr(rag_router, "ingest_raw_text", _fake_ingest_raw_text)

    r = client.post(
        f"/classes/{class_id}/materials",
        data={"raw_text": "hello world", "filename": "notes.txt", "document_type": "notes"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["chunks_created"] == 2
    assert "document_id" in body

