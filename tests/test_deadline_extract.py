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


def test_extract_deadlines_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.deadlines import extract as svc

    payload = json.dumps(
        {
            "deadlines": [
                {
                    "title": "Midterm",
                    "due_text": "Oct 15",
                    "due_at": "2026-10-15T00:00:00Z",
                    "confidence": 0.9,
                    "source_quote": "Midterm: Oct 15",
                }
            ]
        }
    )
    monkeypatch.setattr(svc, "genai", _patch_genai(text=payload))
    with patch(
        "app.services.deadlines.extract.get_settings", return_value=_mock_settings()
    ):
        out = svc.extract_deadlines_from_text(
            filename="syllabus.pdf", raw_text="Midterm Oct 15"
        )
    assert len(out) == 1
    assert out[0].title == "Midterm"
    assert out[0].due_at is not None


def test_extract_deadlines_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.deadlines.extract import DeadlineExtractError
    from app.services.deadlines import extract as svc

    monkeypatch.setattr(svc, "genai", _patch_genai(text="not json"))
    with patch(
        "app.services.deadlines.extract.get_settings", return_value=_mock_settings()
    ):
        with pytest.raises(DeadlineExtractError, match="valid deadlines JSON"):
            svc.extract_deadlines_from_text(filename="s.pdf", raw_text="x")
