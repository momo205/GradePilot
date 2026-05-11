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
    s.gemini_max_retries = 4
    s.gemini_retry_sleep_cap_seconds = 120
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


def test_semester_study_plan_genai_429_maps_to_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from google.genai.errors import ClientError

    from app.services import study_plan_semester as svc
    from app.services.study_plan_semester import SemesterStudyPlanRateLimitError

    err_body = {
        "error": {
            "code": 429,
            "status": "RESOURCE_EXHAUSTED",
            "message": (
                "Quota exceeded. Please retry in 33.5s."
            ),
        }
    }
    monkeypatch.setattr(svc, "genai", _patch_genai(exc=ClientError(429, err_body, None)))
    with patch(
        "app.services.study_plan_semester.get_settings", return_value=_mock_settings()
    ):
        with pytest.raises(SemesterStudyPlanRateLimitError) as ei:
            svc.generate_semester_study_plan(
                class_title="CS101",
                semester_start="2026-09-01",
                semester_end="2026-12-15",
                timezone="America/New_York",
                deadlines=[],
                availability=None,
            )
    assert ei.value.retry_after_seconds == 34


def test_semester_study_plan_retries_transient_429(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from google.genai.errors import ClientError

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
    err = ClientError(
        429,
        {"error": {"code": 429, "message": "Please retry in 0.1s."}},
        None,
    )
    genai_mock = MagicMock()
    client = genai_mock.Client.return_value
    client.models.generate_content.side_effect = [
        err,
        _make_mock_response(payload),
    ]
    monkeypatch.setattr(svc, "genai", genai_mock)
    monkeypatch.setattr(svc.time, "sleep", lambda _s: None)
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
    assert client.models.generate_content.call_count == 2
    assert model == "gemini-test"
    assert out["weeks"][0]["week"] == 1


def test_semester_study_plan_daily_quota_skips_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from google.genai.errors import ClientError

    from app.services import study_plan_semester as svc
    from app.services.study_plan_semester import SemesterStudyPlanRateLimitError

    body = {
        "error": {
            "code": 429,
            "status": "RESOURCE_EXHAUSTED",
            "message": "GenerateRequestsPerDayPerModel-FreeTier exceeded",
        }
    }
    genai_mock = MagicMock()
    client = genai_mock.Client.return_value
    client.models.generate_content.side_effect = ClientError(429, body, None)
    monkeypatch.setattr(svc, "genai", genai_mock)
    sleeps: list[float] = []
    monkeypatch.setattr(svc.time, "sleep", sleeps.append)
    with patch(
        "app.services.study_plan_semester.get_settings", return_value=_mock_settings()
    ):
        with pytest.raises(SemesterStudyPlanRateLimitError):
            svc.generate_semester_study_plan(
                class_title="CS101",
                semester_start="2026-09-01",
                semester_end="2026-12-15",
                timezone="America/New_York",
                deadlines=[],
                availability=None,
            )
    assert client.models.generate_content.call_count == 1
    assert sleeps == []
