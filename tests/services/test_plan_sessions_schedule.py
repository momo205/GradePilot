"""Tests for multi-day study plan calendar scheduling."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import crud
from app.db.models import Base
from app.services.scheduling.plan_sessions import schedule_plan_day_sessions


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


def test_schedule_four_days_calls_upsert_four_times(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each plan day should produce one calendar upsert (per plan_id + day_index)."""
    user_id = uuid.uuid4()
    plan_id = uuid.uuid4()

    crud.upsert_google_integration(
        db=db_session,
        user_id=user_id,
        refresh_token="rt",
        access_token="at",
        token_expiry=None,
        scopes="https://www.googleapis.com/auth/calendar",
    )
    clazz = crud.create_class(db=db_session, user_id=user_id, title="CS 101")
    class_id = clazz.id

    calls: list[int] = []

    def _fake_busy(**kwargs: Any) -> list[tuple[datetime, datetime]]:
        return []

    def _fake_upsert(**kwargs: Any) -> dict[str, str]:
        calls.append(int(kwargs["day_index"]))
        return {
            "event_id": f"evt-{kwargs['day_index']}",
            "html_link": "https://calendar.google.com/event",
        }

    monkeypatch.setattr(
        "app.services.scheduling.plan_sessions.list_busy_blocks", _fake_busy
    )
    monkeypatch.setattr(
        "app.services.scheduling.plan_sessions.has_required_scopes", lambda *_: True
    )
    monkeypatch.setattr(
        "app.services.scheduling.plan_sessions.upsert_plan_day_event",
        _fake_upsert,
    )

    plan_json = {
        "schedule": [
            {"day": "Day 1", "tasks": ["a"]},
            {"day": "Day 2", "tasks": ["b"]},
            {"day": "Day 3", "tasks": ["c"]},
            {"day": "Day 4", "tasks": ["d"]},
        ]
    }

    fixed_now = datetime(2026, 5, 11, 10, 0, 0, tzinfo=timezone.utc)
    results, errors = schedule_plan_day_sessions(
        db=db_session,
        user_id=user_id,
        class_id=class_id,
        plan_id=plan_id,
        plan_json=plan_json,
        class_title="CS 101",
        user_timezone="America/New_York",
        preferred_windows=[{"start": "18:00", "end": "21:00"}],
        now_utc=fixed_now,
    )

    assert not errors
    assert len(results) == 4
    assert sorted(calls) == [0, 1, 2, 3]
