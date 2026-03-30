from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app


def test_auth_me_requires_token() -> None:
    client = TestClient(app)
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_auth_me_ok_with_mocked_verification(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    user_id = str(uuid.uuid4())

    def _fake_verify(_: str) -> dict[str, object]:
        return {"sub": user_id, "role": "authenticated"}

    monkeypatch.setattr("app.deps.auth.verify_supabase_jwt", _fake_verify)

    client = TestClient(app)
    resp = client.get("/auth/me", headers={"Authorization": "Bearer test"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == user_id
    assert body["claims"]["sub"] == user_id
