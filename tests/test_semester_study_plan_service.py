from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


def _make_mock_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    return resp


def _patch_genai(*, text: str | None = None, exc: Exception | None = None) -> MagicMock:
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


def test_semester_study_plan_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import study_plan_semester as svc

    payload = json.dumps(
        {
            "title": "CS101 semester plan",
            "timezone": "America/New_York",
            "semester_start": "2026-09-01",
            "semester_end": "2026-12-15",
            "weeks": [
                {
                    "week": 1,
                    "start": "2026-09-01",
                    "end": "2026-09-07",
                    "goals": ["Set up course"],
                    "tasks": [
                        {
                            "title": "Read syllabus",
                            "estimated_hours": 1.0,
                            "deadline_id": None,
                        }
                    ],
                }
            ],
        }
    )
    monkeypatch.setattr(svc, "genai", _patch_genai(text=payload))
    with patch(
        "app.services.study_plan_semester.get_settings", return_value=_mock_settings()
    ):
        out, model = svc.generate_semester_study_plan(
            class_title="CS101",
            semester_start="2026-09-01",
            semester_end="2026-12-15",
            timezone="America/New_York",
            deadlines=[],
            availability=None,
        )
    assert model == "gemini-test"
    assert out["weeks"][0]["week"] == 1
