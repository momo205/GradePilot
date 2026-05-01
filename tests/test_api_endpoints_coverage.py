from __future__ import annotations

import uuid
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

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


def test_chat_session_create_get_and_post_message_creates_classes(
    client: TestClient,
) -> None:
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


def test_chat_post_message_executes_tool_actions_happy_path(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Drive the chat router through most tool-action branches in one request by
    mocking onboarding output.
    """

    # Create a chat session
    r = client.post("/chat/sessions")
    assert r.status_code == 200
    session_id = r.json()["id"]

    # Seed a class we can refer to later (and ensure db path is exercised)
    r = client.post("/classes", json={"title": "Algorithms"})
    assert r.status_code == 200

    import app.routers.chat as chat_router

    class _Onboarding:
        def __init__(self, state: dict[str, Any], tool_actions: list[dict[str, Any]]):
            self.assistant_message = "ok"
            self.state = state
            self.tool_actions = tool_actions

    # Monkeypatch semester plan generation to avoid external calls.
    def _fake_generate_semester_study_plan(
        *args: Any, **kwargs: Any
    ) -> tuple[dict[str, Any], str]:
        return ({"weeks": [{"week": 1, "tasks": ["read chapter 1"]}]}, "fake-model")

    monkeypatch.setattr(
        chat_router, "generate_semester_study_plan", _fake_generate_semester_study_plan
    )

    # Return tool actions that hit most branches in chat.post_message.
    def _fake_run_onboarding_step(*args: Any, **kwargs: Any) -> _Onboarding:
        state = {
            "phase": "need_syllabi",
            "timezone": "America/New_York",
            "semester_start": "2026-09-01",
            "semester_end": "2026-12-15",
            "availability": [
                {"day": "Mon", "start_time": "09:00", "end_time": "11:00"},
            ],
        }
        tool_actions = [
            {"type": "create_classes", "payload": {"titles": ["Math", "Physics"]}},
            {"type": "create_class", "payload": {"title": "Chemistry"}},
            {
                "type": "set_class_timeline",
                "payload": {
                    "semester_start": "2026-09-01",
                    "semester_end": "2026-12-15",
                    "timezone": "America/New_York",
                    "availability": [
                        {"day": "Tue", "start_time": "10:00", "end_time": "12:00"},
                    ],
                },
            },
            {
                "type": "create_deadline",
                "payload": {"title": "HW1", "due_text": "next week"},
            },
            {"type": "generate_semester_plan", "payload": {}},
            {"type": "complete", "payload": {}},
        ]
        return _Onboarding(state=state, tool_actions=tool_actions)

    monkeypatch.setattr(chat_router, "run_onboarding_step", _fake_run_onboarding_step)

    r = client.post(
        f"/chat/sessions/{session_id}/messages",
        json={"content": "hello"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["session"]["id"] == session_id
    assert body["complete"] is True
    assert body["class_id"] is not None
    assert body["next_url"].startswith("/classes/")


def test_rag_ask_returns_fallback_when_no_chunks(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Create class to satisfy "Class not found" check.
    r = client.post("/classes", json={"title": "History"})
    assert r.status_code == 200
    class_id = r.json()["id"]

    import app.routers.rag as rag_router

    def _fake_retrieve_chunks(*args: Any, **kwargs: Any) -> list[Any]:
        return []

    monkeypatch.setattr(rag_router, "retrieve_chunks", _fake_retrieve_chunks)

    r = client.post(f"/classes/{class_id}/ask", json={"question": "What is the exam?"})
    assert r.status_code == 200
    out = r.json()
    assert out["sources"] == []
    assert "don't have enough information" in out["answer"].lower()


def test_rag_upload_material_raw_text_path(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    r = client.post("/classes", json={"title": "Biology"})
    assert r.status_code == 200
    class_id = r.json()["id"]

    import app.routers.rag as rag_router

    class _Result:
        def __init__(self) -> None:
            self.document_id = uuid.uuid4()
            self.chunks_created = 2

    def _fake_ingest_raw_text(*args: Any, **kwargs: Any) -> _Result:
        return _Result()

    monkeypatch.setattr(rag_router, "ingest_raw_text", _fake_ingest_raw_text)

    r = client.post(
        f"/classes/{class_id}/materials",
        data={
            "raw_text": "hello world",
            "filename": "notes.txt",
            "document_type": "notes",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["chunks_created"] == 2
    assert "document_id" in body


def test_classes_notes_deadlines_and_plans_endpoints(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    r = client.post("/classes", json={"title": "Databases"})
    assert r.status_code == 200
    class_id = r.json()["id"]

    # Notes
    r = client.post(f"/classes/{class_id}/notes", json={"notes_text": "hello"})
    assert r.status_code == 200
    notes_id = r.json()["id"]

    r = client.get(f"/classes/{class_id}/notes")
    assert r.status_code == 200
    assert any(n["id"] == notes_id for n in r.json())

    # Deadlines CRUD
    r = client.post(
        f"/classes/{class_id}/deadlines",
        json={"title": "Midterm", "due": "2026-10-15"},
    )
    assert r.status_code == 200
    deadline_id = r.json()["id"]

    r = client.get(f"/classes/{class_id}/deadlines")
    assert r.status_code == 200
    assert any(d["id"] == deadline_id for d in r.json())

    r = client.patch(
        f"/classes/{class_id}/deadlines/{deadline_id}",
        json={"completed": True},
    )
    assert r.status_code == 200
    assert r.json()["completed_at"] is not None

    # Timeline update
    r = client.patch(
        f"/classes/{class_id}",
        json={
            "semester_start": "2026-09-01",
            "semester_end": "2026-12-15",
            "timezone": "America/New_York",
            "availability": [
                {"day": "Mon", "start_time": "09:00", "end_time": "10:00"}
            ],
        },
    )
    assert r.status_code == 200

    # Mock practice generation
    import app.routers.classes as classes_router

    def _fake_generate_practice_questions(
        *args: Any, **kwargs: Any
    ) -> list[dict[str, Any]]:
        return [{"q": "What is SQL?", "a": "Structured Query Language"}]

    monkeypatch.setattr(
        classes_router, "generate_practice_questions", _fake_generate_practice_questions
    )

    r = client.post(
        f"/classes/{class_id}/practice",
        json={"topic": "SQL", "count": 1, "difficulty": "easy"},
    )
    assert r.status_code == 200
    assert len(r.json()["questions"]) == 1

    # Mock study plan generation
    def _fake_generate_study_plan(
        *args: Any, **kwargs: Any
    ) -> tuple[dict[str, Any], str]:
        return ({"days": [{"day": 1, "tasks": ["read notes"]}]}, "fake-model")

    monkeypatch.setattr(
        classes_router, "generate_study_plan", _fake_generate_study_plan
    )

    r = client.post(f"/classes/{class_id}/study-plan", json={"notes_id": notes_id})
    assert r.status_code == 200
    plan_id = r.json()["id"]

    r = client.get(f"/classes/{class_id}/study-plan/latest")
    assert r.status_code == 200
    assert r.json()["id"] == plan_id

    # Mock semester plan generation
    def _fake_generate_semester_plan(
        *args: Any, **kwargs: Any
    ) -> tuple[dict[str, Any], str]:
        return ({"weeks": [{"week": 1, "tasks": ["do HW1"]}]}, "fake-model")

    monkeypatch.setattr(
        classes_router, "generate_semester_study_plan", _fake_generate_semester_plan
    )

    r = client.post(
        f"/classes/{class_id}/study-plan/semester",
        json={
            "semester_start": "2026-09-01",
            "semester_end": "2026-12-15",
            "timezone": "America/New_York",
            "availability": [
                {"day": "Mon", "start_time": "09:00", "end_time": "10:00"}
            ],
        },
    )
    assert r.status_code == 200

    # Delete deadline
    r = client.delete(f"/classes/{class_id}/deadlines/{deadline_id}")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
