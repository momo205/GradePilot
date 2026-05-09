from __future__ import annotations

import uuid
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base
from app.db.session import get_db
from app.deps.auth import CurrentUser, get_current_user
from app.main import app


def test_settings_defaults_and_update() -> None:
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

    r1 = client.get("/settings")
    assert r1.status_code == 200
    body = r1.json()
    assert body["notificationsEnabled"] is True
    assert body["daysBeforeDeadline"] == 3
    assert body["preferredStudyWindows"] == []
    assert body["autoScheduleSessions"] is False

    r2 = client.put(
        "/settings",
        json={
            "notificationsEnabled": False,
            "daysBeforeDeadline": 7,
            "preferredStudyWindows": [
                {"start": "07:00", "end": "10:00"},
                {"start": "19:00", "end": "23:00"},
            ],
            "autoScheduleSessions": True,
        },
    )
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["notificationsEnabled"] is False
    assert body2["daysBeforeDeadline"] == 7
    assert body2["preferredStudyWindows"] == [
        {"start": "07:00", "end": "10:00"},
        {"start": "19:00", "end": "23:00"},
    ]
    assert body2["autoScheduleSessions"] is True

    # Validation: max 4 windows.
    r3 = client.put(
        "/settings",
        json={
            "preferredStudyWindows": [
                {"start": "06:00", "end": "07:00"},
                {"start": "08:00", "end": "09:00"},
                {"start": "10:00", "end": "11:00"},
                {"start": "12:00", "end": "13:00"},
                {"start": "14:00", "end": "15:00"},
            ],
        },
    )
    assert r3.status_code == 422

    # Validation: start >= end is rejected.
    r4 = client.put(
        "/settings",
        json={"preferredStudyWindows": [{"start": "10:00", "end": "09:00"}]},
    )
    assert r4.status_code == 422

    # Validation: bad HH:MM format is rejected.
    r5 = client.put(
        "/settings",
        json={"preferredStudyWindows": [{"start": "7:00", "end": "10:00"}]},
    )
    assert r5.status_code == 422

    app.dependency_overrides.clear()
