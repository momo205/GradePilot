from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import crud
from app.db.models import Base
from app.db.session import get_db
from app.deps.auth import CurrentUser, get_current_user
from app.main import app


class SchedulingTestClient(TestClient):
    SessionLocal: sessionmaker[Session]
    user_uuid: uuid.UUID
    create_calls: list[dict[str, Any]]


def _override_sqlite_db(url: str) -> tuple[sessionmaker[Session], Any]:
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
        timezone="America/New_York",
        availability_json={"blocks": []},
    )
    return clazz.id


def _seed_google_integration(*, db: Session, user_id: uuid.UUID) -> None:
    crud.upsert_google_integration(
        db=db,
        user_id=user_id,
        refresh_token="rt",
        access_token="at",
        token_expiry=None,
        scopes="https://www.googleapis.com/auth/calendar",
    )


def _set_user_settings(
    *,
    db: Session,
    user_id: uuid.UUID,
    auto_schedule: bool,
    windows: list[dict[str, str]],
) -> None:
    crud.upsert_user_settings(
        db=db,
        user_id=user_id,
        timezone="America/New_York",
        preferred_study_windows=windows,
        auto_schedule_sessions=auto_schedule,
    )


def _far_future_now() -> datetime:
    """A fixed 'now' that's mid-semester so anchors don't get capped weirdly."""
    return datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)


@pytest.fixture()
def client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> Generator[SchedulingTestClient, None, None]:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    db_path = tmp_path / "scheduling_test.db"
    url = f"sqlite+pysqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost/callback")

    SessionLocal, override_get_db = _override_sqlite_db(url=url)
    user_uuid = uuid.uuid4()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = _override_user(user_uuid)

    # Stub the Gemini call so generate_plan succeeds on notes_added.
    import app.agents.replanner.nodes as nodes_mod

    def _fake_generate_semester_study_plan(
        **kwargs: Any,
    ) -> tuple[dict[str, Any], str]:
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

    # Mock Google calendar surface used by schedule_study_session. We patch
    # the *names imported inside the node*, which means patching the module
    # the node imports from (app.services.google_calendar). The local imports
    # inside the node mean the module attributes are looked up at call time.
    import app.services.google_calendar as gc_mod

    create_calls: list[dict[str, Any]] = []

    def _fake_list_busy_blocks(
        **kwargs: Any,
    ) -> list[tuple[datetime, datetime]]:
        return list(getattr(_fake_list_busy_blocks, "blocks", []))

    _fake_list_busy_blocks.blocks = []  # type: ignore[attr-defined]

    def _fake_create_event(**kwargs: Any) -> dict[str, str]:
        create_calls.append(kwargs)
        return {
            "event_id": "evt-fake",
            "html_link": "https://calendar.google.com/event?eid=evt-fake",
        }

    def _fake_has_required_scopes(integration: Any) -> bool:
        return True

    monkeypatch.setattr(gc_mod, "list_busy_blocks", _fake_list_busy_blocks)
    monkeypatch.setattr(gc_mod, "create_study_session_event", _fake_create_event)
    monkeypatch.setattr(gc_mod, "has_required_scopes", _fake_has_required_scopes)

    # Pin "now" inside the node so anchor + slot finder produce predictable
    # results across test runs.
    fixed_now = _far_future_now()

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:  # type: ignore[override]
            return fixed_now if tz is None else fixed_now.astimezone(tz)

    monkeypatch.setattr(nodes_mod, "datetime", _FrozenDatetime)

    with SchedulingTestClient(app) as c:
        c.SessionLocal = SessionLocal
        c.user_uuid = user_uuid
        c.create_calls = create_calls
        yield c

    app.dependency_overrides.clear()


def _trigger_replan(
    client: SchedulingTestClient, class_id: uuid.UUID, trigger: str
) -> dict[str, Any]:
    resp = client.post(
        f"/classes/{class_id}/replan",
        json={"trigger": trigger, "force_replan": False},
    )
    assert resp.status_code == 200, resp.text
    body: dict[str, Any] = resp.json()
    return body


def test_notes_added_with_auto_schedule_off_does_not_create_session(
    client: SchedulingTestClient,
) -> None:
    db = client.SessionLocal()
    user_id = client.user_uuid
    class_id = _seed_class(db=db, user_id=user_id)
    _seed_google_integration(db=db, user_id=user_id)
    _set_user_settings(
        db=db,
        user_id=user_id,
        auto_schedule=False,
        windows=[{"start": "19:00", "end": "23:00"}],
    )
    crud.create_notes(db=db, user_id=user_id, class_id=class_id, notes_text="Lecture 1")
    db.close()

    body = _trigger_replan(client, class_id, "notes_added")
    assert body["scheduled_session"] is None
    assert body["errors"] == []
    assert client.create_calls == []


def test_notes_added_creates_session_in_preferred_window(
    client: SchedulingTestClient,
) -> None:
    db = client.SessionLocal()
    user_id = client.user_uuid
    class_id = _seed_class(db=db, user_id=user_id)
    _seed_google_integration(db=db, user_id=user_id)
    _set_user_settings(
        db=db,
        user_id=user_id,
        auto_schedule=True,
        windows=[{"start": "19:00", "end": "23:00"}],
    )
    crud.create_notes(db=db, user_id=user_id, class_id=class_id, notes_text="Lecture 1")
    db.close()

    body = _trigger_replan(client, class_id, "notes_added")
    sched = body["scheduled_session"]
    assert sched is not None, body
    assert sched["in_preferred_window"] is True
    assert sched["calendar_event_link"].startswith("https://calendar.google.com")
    assert len(client.create_calls) == 1

    # Slot must fall inside the preferred 19:00-23:00 NY window.
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo

    start_ny = _dt.fromisoformat(sched["start"]).astimezone(
        ZoneInfo("America/New_York")
    )
    end_ny = _dt.fromisoformat(sched["end"]).astimezone(ZoneInfo("America/New_York"))
    assert 19 <= start_ny.hour < 23
    assert end_ny.hour <= 23


def test_notes_added_falls_back_outside_preferred_when_busy(
    client: SchedulingTestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = client.SessionLocal()
    user_id = client.user_uuid
    class_id = _seed_class(db=db, user_id=user_id)
    _seed_google_integration(db=db, user_id=user_id)
    _set_user_settings(
        db=db,
        user_id=user_id,
        auto_schedule=True,
        windows=[{"start": "19:00", "end": "23:00"}],
    )
    crud.create_notes(db=db, user_id=user_id, class_id=class_id, notes_text="Lecture 1")
    db.close()

    # Block out every preferred 19-23 NY window between now and 7 days later.
    import app.services.google_calendar as gc_mod
    from zoneinfo import ZoneInfo

    ny = ZoneInfo("America/New_York")
    base_local = _far_future_now().astimezone(ny).date()
    blocks: list[tuple[datetime, datetime]] = []
    for offset in range(8):
        day = base_local + timedelta(days=offset)
        s = datetime(day.year, day.month, day.day, 19, 0, tzinfo=ny)
        e = datetime(day.year, day.month, day.day, 23, 0, tzinfo=ny)
        blocks.append((s.astimezone(timezone.utc), e.astimezone(timezone.utc)))

    def _busy(**kwargs: Any) -> list[tuple[datetime, datetime]]:
        return blocks

    monkeypatch.setattr(gc_mod, "list_busy_blocks", _busy)

    body = _trigger_replan(client, class_id, "notes_added")
    sched = body["scheduled_session"]
    assert sched is not None, body
    assert sched["in_preferred_window"] is False
    assert len(client.create_calls) == 1


def test_notes_added_with_no_google_integration_skips_silently(
    client: SchedulingTestClient,
) -> None:
    db = client.SessionLocal()
    user_id = client.user_uuid
    class_id = _seed_class(db=db, user_id=user_id)
    # No google integration seeded.
    _set_user_settings(
        db=db,
        user_id=user_id,
        auto_schedule=True,
        windows=[{"start": "19:00", "end": "23:00"}],
    )
    crud.create_notes(db=db, user_id=user_id, class_id=class_id, notes_text="Lecture 1")
    db.close()

    body = _trigger_replan(client, class_id, "notes_added")
    assert body["scheduled_session"] is None
    assert body["errors"] == []
    assert client.create_calls == []


def test_deadline_added_does_not_invoke_schedule_node(
    client: SchedulingTestClient,
) -> None:
    db = client.SessionLocal()
    user_id = client.user_uuid
    class_id = _seed_class(db=db, user_id=user_id)
    _seed_google_integration(db=db, user_id=user_id)
    _set_user_settings(
        db=db,
        user_id=user_id,
        auto_schedule=True,
        windows=[{"start": "19:00", "end": "23:00"}],
    )
    crud.create_deadline(
        db=db,
        user_id=user_id,
        class_id=class_id,
        title="HW1",
        due_text="2026-09-30",
        due_at=datetime(2026, 9, 30, 23, 59, tzinfo=timezone.utc),
    )
    db.close()

    body = _trigger_replan(client, class_id, "deadline_added")
    assert body["scheduled_session"] is None
    assert client.create_calls == []
