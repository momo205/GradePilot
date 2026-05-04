from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base
from app.db.session import get_db
from app.deps.auth import CurrentUser, get_current_user
from app.main import app


def test_google_calendar_sync_uses_links(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # In-memory DB
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

    # Settings (OAuth config present)
    def _fake_settings():  # type: ignore[no-untyped-def]
        s = type("S", (), {})()
        s.supabase_url = "x"
        s.supabase_jwt_issuer = "x"
        s.supabase_jwks_url = "x"
        s.supabase_jwt_audience = "authenticated"
        s.supabase_jwt_secret = "x"
        s.database_url = "sqlite+pysqlite://"
        s.google_api_key = None
        s.google_model = "x"
        s.google_embedding_model = "x"
        s.google_oauth_client_id = "cid"
        s.google_oauth_client_secret = "csec"
        s.google_oauth_redirect_uri = "http://localhost/callback"
        return s

    monkeypatch.setattr("app.routers.integrations_google.get_settings", _fake_settings)

    # Mock google calendar service functions
    monkeypatch.setattr(
        "app.routers.integrations_google.build_google_credentials_for_calendar",
        lambda **_: object(),
    )
    monkeypatch.setattr(
        "app.routers.integrations_google.get_or_create_gradepilot_calendar",
        lambda **_: "cal-1",
    )

    seen: list[dict[str, Any]] = []

    def _fake_upsert_deadline_event(**kwargs):  # type: ignore[no-untyped-def]
        seen.append(kwargs)
        return type("U", (), {"calendar_id": "cal-1", "event_id": "evt-1"})()

    monkeypatch.setattr(
        "app.routers.integrations_google.upsert_deadline_event",
        _fake_upsert_deadline_event,
    )

    # Seed DB objects
    from app.db import crud

    with SessionLocal() as db:
        clazz = crud.create_class(db=db, user_id=user_uuid, title="Math")
        class_id = clazz.id
        crud.create_deadline(
            db=db,
            user_id=user_uuid,
            class_id=class_id,
            title="HW1",
            due_text="Oct 1",
            due_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
        crud.upsert_google_integration(
            db=db,
            user_id=user_uuid,
            refresh_token="rt",
            access_token="at",
            token_expiry=None,
            scopes="scope",
        )

    client = TestClient(app)
    resp = client.post(f"/integrations/google/calendar/sync/{class_id}")
    assert resp.status_code == 200
    assert resp.json()["created"] == 1
    assert len(seen) == 1

    app.dependency_overrides.clear()
