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
    assert r1.json()["notificationsEnabled"] is True
    assert r1.json()["daysBeforeDeadline"] == 3

    r2 = client.put(
        "/settings", json={"notificationsEnabled": False, "daysBeforeDeadline": 7}
    )
    assert r2.status_code == 200
    assert r2.json()["notificationsEnabled"] is False
    assert r2.json()["daysBeforeDeadline"] == 7

    app.dependency_overrides.clear()
