"""Unit tests for service-layer and core modules to hit coverage gaps."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# practice service
# ---------------------------------------------------------------------------


def _make_mock_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    return resp


def _patch_genai(*, text: str | None = None, exc: Exception | None = None) -> Any:
    """Patch `from google import genai` usage in services.

    The services now call: `genai.Client(...).models.generate_content(...)`.
    """

    genai_mock = MagicMock()
    client = genai_mock.Client.return_value
    if exc is not None:
        client.models.generate_content.side_effect = exc
    else:
        client.models.generate_content.return_value = _make_mock_response(text or "")
    return genai_mock


def _mock_settings(api_key: str = "test-key", model: str = "gemini-test") -> MagicMock:
    s = MagicMock()
    s.google_api_key = api_key
    s.google_model = model
    return s


def test_practice_service_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import practice as svc

    payload = json.dumps(
        {"questions": [{"q": "What is O(n)?", "a": "Linear time complexity."}]}
    )
    monkeypatch.setattr(svc, "genai", _patch_genai(text=payload))
    with patch("app.services.practice.get_settings", return_value=_mock_settings()):
        result = svc.generate_practice_questions(
            class_title="CS 101", topic="Big-O", count=1, difficulty="Easy"
        )
    assert len(result) == 1
    assert result[0].q == "What is O(n)?"


def test_practice_service_list_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Model returns a bare list instead of wrapped object."""
    from app.services import practice as svc

    payload = json.dumps(
        [{"q": "Define recursion.", "a": "A function calling itself."}]
    )
    monkeypatch.setattr(svc, "genai", _patch_genai(text=payload))
    with patch("app.services.practice.get_settings", return_value=_mock_settings()):
        result = svc.generate_practice_questions(
            class_title="CS 101", topic="Recursion", count=1, difficulty="Medium"
        )
    assert result[0].q == "Define recursion."


def test_practice_service_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.practice import PracticeGenerationError
    from app.services import practice as svc

    monkeypatch.setattr(svc, "genai", _patch_genai(text="not json at all"))
    with patch("app.services.practice.get_settings", return_value=_mock_settings()):
        with pytest.raises(PracticeGenerationError, match="valid questions JSON"):
            svc.generate_practice_questions(
                class_title="CS 101", topic="X", count=1, difficulty="Hard"
            )


def test_practice_service_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.practice import PracticeGenerationError
    from app.services import practice as svc

    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    # Force settings to reload without the key
    with patch("app.services.practice.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(google_api_key=None)
        with pytest.raises(PracticeGenerationError, match="GOOGLE_API_KEY"):
            svc.generate_practice_questions(
                class_title="CS 101", topic="X", count=1, difficulty="Easy"
            )


def test_practice_service_model_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.practice import PracticeGenerationError
    from app.services import practice as svc

    monkeypatch.setattr(svc, "genai", _patch_genai(exc=RuntimeError("network error")))
    with patch("app.services.practice.get_settings", return_value=_mock_settings()):
        with pytest.raises(PracticeGenerationError, match="RuntimeError"):
            svc.generate_practice_questions(
                class_title="CS 101", topic="X", count=1, difficulty="Easy"
            )


# ---------------------------------------------------------------------------
# study_plan service
# ---------------------------------------------------------------------------


def test_study_plan_service_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import study_plan as svc

    payload = json.dumps(
        {
            "title": "CS Plan",
            "goals": ["Understand sorting"],
            "schedule": [{"day": "Day 1", "tasks": ["Read chapter 1"]}],
        }
    )
    monkeypatch.setattr(svc, "genai", _patch_genai(text=payload))
    with patch("app.services.study_plan.get_settings", return_value=_mock_settings()):
        plan, model_name = svc.generate_study_plan(
            class_title="CS 101", notes_text="Sorting algorithms notes."
        )
    assert plan["title"] == "CS Plan"
    assert model_name == "gemini-test"


def test_study_plan_service_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.study_plan import StudyPlanGenerationError
    from app.services import study_plan as svc

    monkeypatch.setattr(svc, "genai", _patch_genai(text="bad json"))
    with patch("app.services.study_plan.get_settings", return_value=_mock_settings()):
        with pytest.raises(StudyPlanGenerationError, match="valid study-plan JSON"):
            svc.generate_study_plan(class_title="CS 101", notes_text="notes")


def test_study_plan_service_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.study_plan import StudyPlanGenerationError
    from app.services import study_plan as svc

    with patch("app.services.study_plan.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(google_api_key=None)
        with pytest.raises(StudyPlanGenerationError, match="GOOGLE_API_KEY"):
            svc.generate_study_plan(class_title="CS 101", notes_text="notes")


def test_study_plan_service_model_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.study_plan import StudyPlanGenerationError
    from app.services import study_plan as svc

    monkeypatch.setattr(svc, "genai", _patch_genai(exc=RuntimeError("timeout")))
    with patch("app.services.study_plan.get_settings", return_value=_mock_settings()):
        with pytest.raises(StudyPlanGenerationError, match="RuntimeError"):
            svc.generate_study_plan(class_title="CS 101", notes_text="notes")


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------


def test_get_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    monkeypatch.delenv("SUPABASE_JWT_ISSUER", raising=False)
    monkeypatch.delenv("SUPABASE_JWKS_URL", raising=False)
    monkeypatch.delenv("GOOGLE_MODEL", raising=False)

    s = config.get_settings()
    assert s.supabase_url == "https://example.supabase.co"
    assert s.supabase_jwt_issuer == "https://example.supabase.co/auth/v1"
    assert ".well-known/jwks.json" in s.supabase_jwks_url
    assert s.google_model == "gemini-2.5-flash"


def test_get_settings_missing_supabase_url(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.delenv("SUPABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        config.get_settings()


def test_get_settings_missing_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        config.get_settings()


def test_get_settings_custom_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import config

    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    monkeypatch.setenv("SUPABASE_JWT_ISSUER", "https://custom-issuer.example.com")
    monkeypatch.setenv("SUPABASE_JWKS_URL", "https://custom-issuer.example.com/jwks")

    s = config.get_settings()
    assert s.supabase_jwt_issuer == "https://custom-issuer.example.com"
    assert s.supabase_jwks_url == "https://custom-issuer.example.com/jwks"


# ---------------------------------------------------------------------------
# security
# ---------------------------------------------------------------------------


def test_verify_jwt_unsupported_alg(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import security

    with (
        patch("app.core.security.jwt.get_unverified_header") as mock_header,
        patch("app.core.security.jwt.get_unverified_claims") as mock_claims,
    ):
        mock_header.return_value = {"alg": "none"}
        mock_claims.return_value = {"sub": "user-1", "aud": "authenticated"}
        with patch("app.core.security.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                supabase_jwt_audience="authenticated",
                supabase_jwt_issuer="https://example.supabase.co/auth/v1",
                supabase_jwt_secret="secret",
            )
            with pytest.raises(ValueError, match="Unsupported token algorithm"):
                security.verify_supabase_jwt("fake.token.here")


def test_verify_jwt_hs256_missing_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import security

    with (
        patch("app.core.security.jwt.get_unverified_header") as mock_header,
        patch("app.core.security.jwt.get_unverified_claims") as mock_claims,
        patch("app.core.security.get_settings") as mock_settings,
    ):
        mock_header.return_value = {"alg": "HS256"}
        mock_claims.return_value = {"sub": "user-1"}
        mock_settings.return_value = MagicMock(
            supabase_jwt_secret=None,
            supabase_jwt_audience="authenticated",
            supabase_jwt_issuer="https://example.supabase.co/auth/v1",
        )
        with pytest.raises(ValueError, match="SUPABASE_JWT_SECRET"):
            security.verify_supabase_jwt("fake.token.here")


def test_get_jwks_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import security

    fake_jwks: dict[str, Any] = {"keys": [{"kid": "abc"}]}
    cached = security.JWKSCache(jwks=fake_jwks, expires_at=9999999999.0)
    monkeypatch.setattr(security, "_jwks_cache", cached)
    with patch("app.core.security.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            supabase_jwks_url="https://example.supabase.co/auth/v1/.well-known/jwks.json"
        )
        result = security._get_jwks(now=1000.0)
    assert result == fake_jwks


def test_get_jwks_fetches_when_expired(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import security

    monkeypatch.setattr(security, "_jwks_cache", None)
    fake_jwks: dict[str, Any] = {"keys": []}

    mock_resp = MagicMock()
    mock_resp.json.return_value = fake_jwks

    with (
        patch("app.core.security.httpx.Client") as mock_client_cls,
        patch("app.core.security.get_settings") as mock_settings,
    ):
        mock_settings.return_value = MagicMock(
            supabase_jwks_url="https://example.supabase.co/auth/v1/.well-known/jwks.json"
        )
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = security._get_jwks(now=1000.0)
        assert result == fake_jwks


# ---------------------------------------------------------------------------
# session
# ---------------------------------------------------------------------------


def test_get_engine_normalises_url(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.db import session as sess

    monkeypatch.setattr(sess, "_ENGINE", None)
    monkeypatch.setattr(sess, "_SessionLocal", None)

    with (
        patch("app.db.session.get_settings") as mock_settings,
        patch("app.db.session.create_engine") as mock_engine,
    ):
        mock_settings.return_value = MagicMock(
            database_url="postgresql://user:pass@localhost/db"
        )
        mock_engine.return_value = MagicMock()
        sess.get_engine()
        called_url = mock_engine.call_args[0][0]
        assert called_url.startswith("postgresql+psycopg://")


def test_get_sessionmaker_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.db import session as sess

    monkeypatch.setattr(sess, "_ENGINE", None)
    monkeypatch.setattr(sess, "_SessionLocal", None)

    with patch("app.db.session.get_engine") as mock_engine:
        mock_engine.return_value = MagicMock()
        sm1 = sess._get_sessionmaker()
        sm2 = sess._get_sessionmaker()
        assert sm1 is sm2
        assert mock_engine.call_count == 1
