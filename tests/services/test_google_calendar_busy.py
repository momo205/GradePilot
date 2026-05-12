from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import crud
from app.db.models import Base, GoogleIntegration
from app.services import google_calendar
from app.services.google_calendar import (
    REQUIRED_SCOPES,
    create_study_session_event,
    has_required_scopes,
    list_busy_blocks,
)


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()


def _fake_settings() -> Any:
    s = type("S", (), {})()
    s.google_oauth_client_id = "cid"
    s.google_oauth_client_secret = "csec"
    s.google_oauth_redirect_uri = "http://localhost/callback"
    return s


def test_has_required_scopes_full_scope_passes() -> None:
    integ = GoogleIntegration(
        user_id=uuid.uuid4(),
        refresh_token="rt",
        scopes="https://www.googleapis.com/auth/calendar openid email",
    )
    assert has_required_scopes(integ) is True


def test_has_required_scopes_missing_calendar_fails() -> None:
    integ = GoogleIntegration(
        user_id=uuid.uuid4(),
        refresh_token="rt",
        scopes="openid email",
    )
    assert has_required_scopes(integ) is False


def test_has_required_scopes_empty_string_fails() -> None:
    integ = GoogleIntegration(user_id=uuid.uuid4(), refresh_token="rt", scopes="")
    assert has_required_scopes(integ) is False


def test_required_scopes_set_does_not_include_readonly() -> None:
    # Documents the choice in the source: full calendar implies readonly,
    # so requesting both would be a redundant scope bump.
    assert "https://www.googleapis.com/auth/calendar.readonly" not in REQUIRED_SCOPES


def test_list_busy_blocks_no_integration_returns_empty(
    db_session: Session,
) -> None:
    user_id = uuid.uuid4()
    out = list_busy_blocks(
        db=db_session,
        user_id=str(user_id),
        start=datetime(2026, 9, 14, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc),
    )
    assert out == []


def test_list_busy_blocks_insufficient_scopes_returns_empty(
    db_session: Session,
) -> None:
    user_id = uuid.uuid4()
    crud.upsert_google_integration(
        db=db_session,
        user_id=user_id,
        refresh_token="rt",
        access_token="at",
        token_expiry=None,
        scopes="openid email",
    )
    out = list_busy_blocks(
        db=db_session,
        user_id=str(user_id),
        start=datetime(2026, 9, 14, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc),
    )
    assert out == []


def test_list_busy_blocks_naive_dt_raises(db_session: Session) -> None:
    with pytest.raises(ValueError):
        list_busy_blocks(
            db=db_session,
            user_id=str(uuid.uuid4()),
            start=datetime(2026, 9, 14, 0, 0),
            end=datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc),
        )


def test_list_busy_blocks_end_before_start_returns_empty(
    db_session: Session,
) -> None:
    out = list_busy_blocks(
        db=db_session,
        user_id=str(uuid.uuid4()),
        start=datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 9, 14, 0, 0, tzinfo=timezone.utc),
    )
    assert out == []


def _seed_full_scope_integration(db: Session, user_id: uuid.UUID) -> None:
    crud.upsert_google_integration(
        db=db,
        user_id=user_id,
        refresh_token="rt",
        access_token="at",
        token_expiry=None,
        scopes="https://www.googleapis.com/auth/calendar",
    )


def test_list_busy_blocks_returns_merged_intervals(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id = uuid.uuid4()
    _seed_full_scope_integration(db_session, user_id)

    monkeypatch.setattr(google_calendar, "get_settings", _fake_settings)
    monkeypatch.setattr(
        google_calendar,
        "build_google_credentials_for_calendar",
        lambda **_: object(),
    )
    monkeypatch.setattr(
        google_calendar,
        "get_or_create_gradepilot_calendar",
        lambda **_: "cal-gp",
    )

    # freebusy.query returns busy on primary + GradePilot; all merge together.
    fake_response = {
        "calendars": {
            "primary": {
                "busy": [
                    {"start": "2026-09-15T13:00:00Z", "end": "2026-09-15T14:00:00Z"},
                    {"start": "2026-09-15T14:00:00Z", "end": "2026-09-15T15:30:00Z"},
                    {"start": "2026-09-16T10:00:00Z", "end": "2026-09-16T11:00:00Z"},
                ]
            },
            "cal-gp": {
                "busy": [
                    {"start": "2026-09-16T11:00:00Z", "end": "2026-09-16T12:00:00Z"},
                ]
            },
        }
    }

    captured_body: dict[str, Any] = {}

    fake_query = MagicMock()
    fake_query.execute.return_value = fake_response
    fake_freebusy = MagicMock()

    def _query_side_effect(body: dict[str, Any]) -> MagicMock:
        captured_body.update(body)
        return fake_query

    fake_freebusy.query.side_effect = _query_side_effect

    fake_svc = MagicMock()
    fake_svc.freebusy.return_value = fake_freebusy

    monkeypatch.setattr(google_calendar, "build", lambda *a, **kw: fake_svc)

    out = list_busy_blocks(
        db=db_session,
        user_id=str(user_id),
        start=datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 9, 17, 0, 0, tzinfo=timezone.utc),
    )

    assert captured_body["timeMin"].startswith("2026-09-15")
    assert captured_body["timeMax"].startswith("2026-09-17")
    assert captured_body["items"] == [{"id": "primary"}, {"id": "cal-gp"}]

    assert out == [
        (
            datetime(2026, 9, 15, 13, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 15, 15, 30, tzinfo=timezone.utc),
        ),
        (
            datetime(2026, 9, 16, 10, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc),
        ),
    ]


def _patch_calendar_writes(
    monkeypatch: pytest.MonkeyPatch, fake_svc: MagicMock
) -> None:
    monkeypatch.setattr(google_calendar, "get_settings", _fake_settings)
    monkeypatch.setattr(
        google_calendar,
        "build_google_credentials_for_calendar",
        lambda **_: object(),
    )
    monkeypatch.setattr(
        google_calendar, "get_or_create_gradepilot_calendar", lambda **_: "cal-gp"
    )
    monkeypatch.setattr(google_calendar, "build", lambda *a, **kw: fake_svc)


def test_create_study_session_event_inserts_and_records_link(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id = uuid.uuid4()
    class_id = uuid.uuid4()
    notes_id = uuid.uuid4()
    _seed_full_scope_integration(db_session, user_id)

    fake_insert_call = MagicMock()
    fake_insert_call.execute.return_value = {
        "id": "evt-1",
        "htmlLink": "https://calendar.google.com/event?eid=evt-1",
    }
    fake_events = MagicMock()
    fake_events.insert.return_value = fake_insert_call
    fake_svc = MagicMock()
    fake_svc.events.return_value = fake_events
    _patch_calendar_writes(monkeypatch, fake_svc)

    out = create_study_session_event(
        db=db_session,
        user_id=str(user_id),
        class_id=class_id,
        notes_id=notes_id,
        title="Study: Lecture 5 notes",
        start=datetime(2026, 9, 15, 19, 0, tzinfo=timezone.utc),
        end=datetime(2026, 9, 15, 20, 0, tzinfo=timezone.utc),
        description="Focused review block.",
    )

    assert out == {
        "event_id": "evt-1",
        "html_link": "https://calendar.google.com/event?eid=evt-1",
    }

    fake_events.insert.assert_called_once()
    body = fake_events.insert.call_args.kwargs["body"]
    assert body["summary"] == "Study: Lecture 5 notes"
    assert "Auto-scheduled by GradePilot." in body["description"]
    assert str(notes_id) in body["description"]
    assert "Focused review block." in body["description"]
    assert body["start"] == {"dateTime": "2026-09-15T19:00:00+00:00"}
    assert body["end"] == {"dateTime": "2026-09-15T20:00:00+00:00"}

    link = crud.get_calendar_event_link(
        db=db_session,
        user_id=user_id,
        kind="study_session",
        local_id=str(notes_id),
    )
    assert link is not None
    assert link.google_event_id == "evt-1"
    assert link.google_calendar_id == "cal-gp"
    assert link.class_id == class_id


def test_create_study_session_event_is_idempotent_via_existing_link(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id = uuid.uuid4()
    class_id = uuid.uuid4()
    notes_id = uuid.uuid4()
    _seed_full_scope_integration(db_session, user_id)

    # Pre-existing link as if a previous run already created the event.
    crud.upsert_calendar_event_link(
        db=db_session,
        user_id=user_id,
        class_id=class_id,
        kind="study_session",
        local_id=str(notes_id),
        google_calendar_id="cal-gp",
        google_event_id="evt-existing",
    )

    fake_patch_call = MagicMock()
    fake_patch_call.execute.return_value = {
        "id": "evt-existing",
        "htmlLink": "https://calendar.google.com/event?eid=evt-existing",
    }
    fake_events = MagicMock()
    fake_events.patch.return_value = fake_patch_call
    fake_svc = MagicMock()
    fake_svc.events.return_value = fake_events
    _patch_calendar_writes(monkeypatch, fake_svc)

    out = create_study_session_event(
        db=db_session,
        user_id=str(user_id),
        class_id=class_id,
        notes_id=notes_id,
        title="Study: updated",
        start=datetime(2026, 9, 16, 19, 0, tzinfo=timezone.utc),
        end=datetime(2026, 9, 16, 20, 0, tzinfo=timezone.utc),
    )
    assert out["event_id"] == "evt-existing"

    fake_events.insert.assert_not_called()
    fake_events.patch.assert_called_once()
    assert fake_events.patch.call_args.kwargs["eventId"] == "evt-existing"


def test_create_study_session_event_naive_dt_raises(db_session: Session) -> None:
    with pytest.raises(ValueError):
        create_study_session_event(
            db=db_session,
            user_id=str(uuid.uuid4()),
            class_id=uuid.uuid4(),
            notes_id=uuid.uuid4(),
            title="Study",
            start=datetime(2026, 9, 15, 19, 0),
            end=datetime(2026, 9, 15, 20, 0, tzinfo=timezone.utc),
        )


def test_create_study_session_event_end_before_start_raises(
    db_session: Session,
) -> None:
    with pytest.raises(ValueError):
        create_study_session_event(
            db=db_session,
            user_id=str(uuid.uuid4()),
            class_id=uuid.uuid4(),
            notes_id=uuid.uuid4(),
            title="Study",
            start=datetime(2026, 9, 15, 20, 0, tzinfo=timezone.utc),
            end=datetime(2026, 9, 15, 19, 0, tzinfo=timezone.utc),
        )


def test_create_study_session_event_no_integration_raises(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(google_calendar, "get_settings", _fake_settings)
    with pytest.raises(RuntimeError, match="not connected"):
        create_study_session_event(
            db=db_session,
            user_id=str(uuid.uuid4()),
            class_id=uuid.uuid4(),
            notes_id=uuid.uuid4(),
            title="Study",
            start=datetime(2026, 9, 15, 19, 0, tzinfo=timezone.utc),
            end=datetime(2026, 9, 15, 20, 0, tzinfo=timezone.utc),
        )


def test_create_study_session_event_insufficient_scopes_raises(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id = uuid.uuid4()
    crud.upsert_google_integration(
        db=db_session,
        user_id=user_id,
        refresh_token="rt",
        access_token="at",
        token_expiry=None,
        scopes="openid email",
    )
    monkeypatch.setattr(google_calendar, "get_settings", _fake_settings)
    with pytest.raises(RuntimeError, match="missing required scopes"):
        create_study_session_event(
            db=db_session,
            user_id=str(user_id),
            class_id=uuid.uuid4(),
            notes_id=uuid.uuid4(),
            title="Study",
            start=datetime(2026, 9, 15, 19, 0, tzinfo=timezone.utc),
            end=datetime(2026, 9, 15, 20, 0, tzinfo=timezone.utc),
        )


def test_list_busy_blocks_freebusy_errors_returns_empty(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id = uuid.uuid4()
    _seed_full_scope_integration(db_session, user_id)

    monkeypatch.setattr(google_calendar, "get_settings", _fake_settings)
    monkeypatch.setattr(
        google_calendar,
        "build_google_credentials_for_calendar",
        lambda **_: object(),
    )
    monkeypatch.setattr(
        google_calendar,
        "get_or_create_gradepilot_calendar",
        lambda **_: "cal-gp",
    )

    fake_query = MagicMock()
    fake_query.execute.return_value = {
        "calendars": {
            "primary": {"errors": [{"reason": "notFound"}]},
            "cal-gp": {"busy": []},
        }
    }
    fake_freebusy = MagicMock()
    fake_freebusy.query.return_value = fake_query
    fake_svc = MagicMock()
    fake_svc.freebusy.return_value = fake_freebusy
    monkeypatch.setattr(google_calendar, "build", lambda *a, **kw: fake_svc)

    out = list_busy_blocks(
        db=db_session,
        user_id=str(user_id),
        start=datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 9, 17, 0, 0, tzinfo=timezone.utc),
    )
    assert out == []
