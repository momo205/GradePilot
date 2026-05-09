"""Live checks against the Google Gemini API (Developer API / google-genai).

These tests call the real network. They are skipped unless:

- ``RUN_LIVE_GEMINI_TESTS=1`` (or ``true`` / ``yes``), and
- ``GOOGLE_API_KEY`` is set (e.g. via ``.env`` when running from the repo root).

Run:

.. code-block:: bash

   RUN_LIVE_GEMINI_TESTS=1 uv run pytest tests/integration/test_gemini_live.py -v

In CI, keep the default ``pytest`` invocation without this env var so nothing is billed.

Tests cover the same SDK paths used for embeddings (RAG) and JSON study plans.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    # Ensure ``GOOGLE_API_KEY`` from ``.env`` is visible before fixtures run (``get_settings`` is not imported yet).
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    load_dotenv()
except Exception:
    pass

import pytest
from google import genai
from google.genai import types
from google.genai.errors import ClientError

pytestmark = pytest.mark.integration

_DEFAULT_CHAT_MODEL = "gemini-2.5-flash"
_DEFAULT_EMBEDDING_MODEL = "models/gemini-embedding-001"
_EMBEDDING_DIM = 768


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes")


def _chat_model() -> str:
    return (os.getenv("GOOGLE_MODEL") or _DEFAULT_CHAT_MODEL).strip()


def _embedding_model() -> str:
    return (os.getenv("GOOGLE_EMBEDDING_MODEL") or _DEFAULT_EMBEDDING_MODEL).strip()


def _gate_live_gemini() -> None:
    """Skip unless live tests are enabled and a key is present (do not return the key — avoids pytest printing it)."""
    if not _truthy_env("RUN_LIVE_GEMINI_TESTS"):
        pytest.skip(
            "Set RUN_LIVE_GEMINI_TESTS=1 to run live Gemini tests (network + API quota)."
        )
    if not (os.getenv("GOOGLE_API_KEY") or "").strip():
        pytest.skip("GOOGLE_API_KEY is not set")


@pytest.fixture
def _live_gemini_gate() -> None:
    _gate_live_gemini()


@pytest.fixture
def live_app_settings(_live_gemini_gate: None) -> object:
    try:
        from app.core.config import get_settings

        return get_settings()
    except RuntimeError as e:
        pytest.skip(f"Full app environment required for get_settings(): {e}")


def _friendly_api_error(e: ClientError) -> str:
    code = getattr(e, "code", None) or getattr(e, "status_code", None)
    msg = str(e)
    if code == 403 or "PERMISSION_DENIED" in msg:
        return (
            "Gemini returned 403 PERMISSION_DENIED — enable the Generative Language API "
            "for this key's Google Cloud project, check billing/quota, or create a new API key."
        )
    if code in (401, 400):
        return "Gemini rejected the request — verify GOOGLE_API_KEY and model names."
    return f"Gemini API error ({e.__class__.__name__})."


def test_gemini_generate_content_connection(_live_gemini_gate: None) -> None:
    """Minimal ``generate_content`` — same family of call as study plans / chat."""
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    model = _chat_model()
    try:
        resp = client.models.generate_content(
            model=model,
            contents='Reply with a single JSON object: {"status":"ok"}',
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=64,
                response_mime_type="application/json",
            ),
        )
    except ClientError as e:
        pytest.fail(_friendly_api_error(e))
    text = (resp.text or "").strip()
    assert text, "empty response text from Gemini"
    assert '"status"' in text and "ok" in text.lower(), f"unexpected body: {text!r}"


def test_gemini_embed_content_connection(_live_gemini_gate: None) -> None:
    """``embed_content`` — same API surface as RAG indexing / search."""
    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    model = _embedding_model()
    try:
        resp = client.models.embed_content(
            model=model,
            contents="GradePilot connectivity probe for retrieval.",
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=_EMBEDDING_DIM,
            ),
        )
    except ClientError as e:
        pytest.fail(_friendly_api_error(e))
    embeddings = getattr(resp, "embeddings", None)
    assert isinstance(embeddings, list) and len(embeddings) > 0
    values = getattr(embeddings[0], "values", None)
    assert isinstance(values, list) and len(values) == _EMBEDDING_DIM
    assert all(isinstance(x, (int, float)) for x in values)


def test_app_embed_query_matches_live_stack(live_app_settings) -> None:
    """Uses ``app.services.rag.embeddings.embed_query`` (requires full app ``Settings``)."""
    from app.services.rag.embeddings import EmbeddingsError, embed_query

    try:
        vec = embed_query(text="short note about photosynthesis")
    except EmbeddingsError as e:
        if isinstance(e.__cause__, ClientError):
            pytest.fail(_friendly_api_error(e.__cause__))
        raise
    assert isinstance(vec, list) and len(vec) == _EMBEDDING_DIM


def test_app_generate_study_plan_matches_live_stack(live_app_settings) -> None:
    """Uses ``generate_study_plan`` — JSON + schema validation path."""
    from app.services.study_plan import StudyPlanGenerationError, generate_study_plan

    try:
        data, model_used = generate_study_plan(
            class_title="Test Class",
            notes_text="Chapter 1: intro. Exam next Friday on chapters 1-2.",
        )
    except StudyPlanGenerationError as e:
        if isinstance(e.__cause__, ClientError):
            pytest.fail(_friendly_api_error(e.__cause__))
        raise
    assert model_used
    assert data.get("title")
    assert isinstance(data.get("goals"), list)
    assert isinstance(data.get("schedule"), list)
    assert len(data["schedule"]) >= 1
