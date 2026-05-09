from __future__ import annotations

import uuid
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import crud
from app.db.models import Base, StudyPlan
from app.db.session import get_db
from app.deps.auth import CurrentUser, get_current_user
from app.main import app


class ReplannerTestClient(TestClient):  # type: ignore[misc]
    """TestClient with session factory and user id attached for replanner API tests."""

    SessionLocal: sessionmaker[Session]
    user_uuid: uuid.UUID


def _override_sqlite_db(*, url: str) -> tuple[sessionmaker[Session], Any]:
    engine = create_engine(
        url,
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def _override_get_db() -> Generator[Session, None, None]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    return SessionLocal, _override_get_db


def _override_user(user_uuid: uuid.UUID) -> Any:
    def _override_get_current_user() -> CurrentUser:
        return CurrentUser(user_id=str(user_uuid), claims={"sub": str(user_uuid)})

    return _override_get_current_user


def _seed_class(*, db: Session, user_id: uuid.UUID) -> uuid.UUID:
    clazz = crud.create_class(db=db, user_id=user_id, title="CS101")
    crud.update_class_timeline(
        db=db,
        user_id=user_id,
        class_id=clazz.id,
        semester_start="2026-09-01",
        semester_end="2026-12-15",
        timezone="UTC",
        availability_json={"blocks": []},
    )
    return clazz.id


def _seed_plan(
    *,
    db: Session,
    user_id: uuid.UUID,
    class_id: uuid.UUID,
    deadline_ids: list[str],
    completed_tasks: list[str] | None = None,
) -> uuid.UUID:
    plan_json: dict[str, Any] = {
        "title": "Plan",
        "timezone": "UTC",
        "semester_start": "2026-09-01",
        "semester_end": "2026-12-15",
        "weeks": [
            {
                "week": 1,
                "start": "2026-09-01",
                "end": "2026-09-07",
                "goals": [],
                "tasks": [
                    {"title": "Task", "estimated_hours": 1.0, "deadline_id": did}
                    for did in deadline_ids
                ],
            }
        ],
    }
    if completed_tasks is not None:
        plan_json["completed_tasks"] = completed_tasks

    plan = crud.create_study_plan(
        db=db,
        user_id=user_id,
        class_id=class_id,
        source_notes_id=None,
        plan_json=plan_json,
        model="fake",
    )
    return plan.id


@pytest.fixture()
def client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> Generator[ReplannerTestClient, None, None]:
    # Required envs for app.core.config.get_settings()
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    db_path = tmp_path / "replanner_test.db"
    url = f"sqlite+pysqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost/callback")

    SessionLocal, override_get_db = _override_sqlite_db(url=url)
    user_uuid = uuid.uuid4()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _override_user(user_uuid)

    # Mock Gemini semester plan generator to avoid real API calls.
    import app.agents.replanner.nodes as nodes_mod

    def _fake_generate_semester_study_plan(**kwargs: Any) -> tuple[dict[str, Any], str]:
        return (
            {
                "title": "Generated",
                "timezone": kwargs["timezone"],
                "semester_start": kwargs["semester_start"],
                "semester_end": kwargs["semester_end"],
                "weeks": [],
            },
            "fake-model",
        )

    monkeypatch.setattr(
        nodes_mod, "generate_semester_study_plan", _fake_generate_semester_study_plan
    )

    with ReplannerTestClient(app) as c:
        c.SessionLocal = SessionLocal
        c.user_uuid = user_uuid
        yield c

    app.dependency_overrides.clear()


def test_gate_skips_when_no_material_change(client: ReplannerTestClient) -> None:
    db: Session = client.SessionLocal()
    user_id = client.user_uuid
    class_id = _seed_class(db=db, user_id=user_id)

    d = crud.create_deadline(
        db=db, user_id=user_id, class_id=class_id, title="HW1", due_text="2026-09-10"
    )
    _seed_plan(db=db, user_id=user_id, class_id=class_id, deadline_ids=[str(d.id)])
    db.close()

    resp = client.post(
        f"/classes/{class_id}/replan",
        json={"trigger": "manual_replan", "force_replan": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["should_replan"] is False
    assert body["replan_reason"] == "no_material_change"


def test_gate_triggers_on_new_deadline(client: ReplannerTestClient) -> None:
    db: Session = client.SessionLocal()
    user_id = client.user_uuid
    class_id = _seed_class(db=db, user_id=user_id)

    d1 = crud.create_deadline(
        db=db, user_id=user_id, class_id=class_id, title="HW1", due_text="2026-09-10"
    )
    _seed_plan(db=db, user_id=user_id, class_id=class_id, deadline_ids=[str(d1.id)])

    # New deadline after plan creation
    crud.create_deadline(
        db=db, user_id=user_id, class_id=class_id, title="HW2", due_text="2026-09-20"
    )
    db.close()

    resp = client.post(
        f"/classes/{class_id}/replan",
        json={"trigger": "deadline_added", "force_replan": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["should_replan"] is True
    assert "new_deadlines" in str(body["replan_reason"])


def test_dry_run_does_not_persist(client: ReplannerTestClient) -> None:
    db: Session = client.SessionLocal()
    user_id = client.user_uuid
    class_id = _seed_class(db=db, user_id=user_id)

    before = db.execute(select(StudyPlan)).scalars().all()
    assert len(before) == 0
    db.close()

    resp = client.post(
        f"/classes/{class_id}/replan",
        json={"trigger": "manual_replan", "dry_run": True, "force_replan": True},
    )
    assert resp.status_code == 200

    db2: Session = client.SessionLocal()
    after = db2.execute(select(StudyPlan)).scalars().all()
    db2.close()
    assert len(after) == 0


def test_completed_tasks_carry_forward(client: ReplannerTestClient) -> None:
    db: Session = client.SessionLocal()
    user_id = client.user_uuid
    class_id = _seed_class(db=db, user_id=user_id)

    d = crud.create_deadline(
        db=db, user_id=user_id, class_id=class_id, title="HW1", due_text="2026-09-10"
    )
    _seed_plan(
        db=db,
        user_id=user_id,
        class_id=class_id,
        deadline_ids=[str(d.id)],
        completed_tasks=["t1", "t2"],
    )
    db.close()

    resp = client.post(
        f"/classes/{class_id}/replan",
        json={"trigger": "manual_replan", "force_replan": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["should_replan"] is True
    assert body["new_plan"]["completed_tasks"] == ["t1", "t2"]


def test_calendar_sync_skipped_without_integration(
    client: ReplannerTestClient,
) -> None:
    db: Session = client.SessionLocal()
    user_id = client.user_uuid
    class_id = _seed_class(db=db, user_id=user_id)
    db.close()

    resp = client.post(
        f"/classes/{class_id}/replan",
        json={"trigger": "manual_replan", "force_replan": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["calendar_sync_result"] is None
    assert body["errors"] == [] or all(
        not str(e).startswith("sync_calendar_") for e in body["errors"]
    )
