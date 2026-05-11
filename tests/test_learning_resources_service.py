from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from google.api_core.exceptions import ResourceExhausted


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


def _mock_settings() -> MagicMock:
    s = MagicMock()
    s.google_api_key = "test-key"
    s.google_model = "gemini-test"
    return s


def test_learning_resources_parses_retry_after_seconds() -> None:
    from app.services import learning_resources as svc

    assert svc._parse_retry_after_seconds("") is None
    assert svc._parse_retry_after_seconds("Please retry in 0.1s.") == 1
    assert svc._parse_retry_after_seconds("please retry in 2s") == 2
    assert svc._parse_retry_after_seconds("Please retry in 2.01s") == 3


def test_generate_learning_resources_happy_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import learning_resources as svc

    payload = json.dumps(
        {
            "items": [
                {
                    "title": "Big-O basics",
                    "rationale": "Build intuition for algorithm runtime.",
                    "destination": "youtube",
                    "search_query": "big o notation explained",
                },
                {
                    "title": "Python data structures docs",
                    "rationale": "Reference for lists, dicts, sets, and complexity.",
                    "destination": "web",
                    "search_query": "python list dict set time complexity documentation",
                },
                {
                    "title": "Sorting algorithms walkthrough",
                    "rationale": "Reinforce comparisons between common sorts.",
                    "destination": "youtube",
                    "search_query": "sorting algorithms visualization bubble merge quick",
                },
                {
                    "title": "Asymptotic analysis notes",
                    "rationale": "Deeper explanation and worked examples.",
                    "destination": "web",
                    "search_query": "asymptotic analysis examples big o theta omega",
                },
                {
                    "title": "Recursion lecture",
                    "rationale": "Solidify recursion patterns and base/recursive cases.",
                    "destination": "youtube",
                    "search_query": "recursion introduction computer science lecture",
                },
            ]
        }
    )
    monkeypatch.setattr(svc, "genai", _patch_genai(text=payload))
    with patch(
        "app.services.learning_resources.get_settings", return_value=_mock_settings()
    ):
        items, model = svc.generate_learning_resources(
            class_title="CS101",
            note_segments=[("Lecture 1", "Big-O and recursion basics.")],
        )

    assert model == "gemini-test"
    assert len(items) >= 5
    assert items[0].title


def test_generate_learning_resources_rate_limit_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import learning_resources as svc

    exc = ResourceExhausted("Please retry in 0.1s.")
    monkeypatch.setattr(svc, "genai", _patch_genai(exc=exc))

    with patch(
        "app.services.learning_resources.get_settings", return_value=_mock_settings()
    ):
        with pytest.raises(svc.LearningResourcesRateLimitError) as e:
            svc.generate_learning_resources(
                class_title="CS101",
                note_segments=[("Lecture 1", "Big-O and recursion basics.")],
            )

    assert e.value.retry_after_seconds == 1
