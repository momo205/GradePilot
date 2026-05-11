from __future__ import annotations

import json
import logging
import re
from google.api_core.exceptions import ResourceExhausted
from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas import LearningResourceItem, LearningResourcesAI

logger = logging.getLogger("gradepilot.ai")

_RESOURCE_MIN = 5
_RESOURCE_MAX = 8

_RETRY_RE = re.compile(r"Please retry in\s+([0-9]+(?:\.[0-9]+)?)s", re.IGNORECASE)


def _parse_retry_after_seconds(msg: str) -> int | None:
    m = _RETRY_RE.search(msg or "")
    if not m:
        return None
    try:
        return max(1, int(float(m.group(1)) + 0.999))
    except Exception:
        return None


class LearningResourcesError(RuntimeError):
    pass


class LearningResourcesRateLimitError(LearningResourcesError):
    def __init__(self, message: str, *, retry_after_seconds: int | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def _format_note_segments(note_segments: list[tuple[str, str]]) -> str:
    parts: list[str] = []
    for label, text in note_segments:
        parts.append(f"### {label}\n{text.strip()}")
    return "\n\n".join(parts)


def _build_prompt(
    *,
    class_title: str,
    note_segments: list[tuple[str, str]],
) -> str:
    material = _format_note_segments(note_segments)
    return f"""You are a helpful study coach for university and high school students.

Course title: "{class_title}"

Below are the student's saved lecture notes (may be incomplete).

--- BEGIN NOTES ---
{material}
--- END NOTES ---

Suggest between {_RESOURCE_MIN} and {_RESOURCE_MAX} learning resources to supplement this course.

Rules:
- Return ONLY valid JSON, no markdown, no extra text.
- Each item must have: "title" (short label), "rationale" (1-3 sentences why it helps for THIS course),
  "destination" (either "youtube" or "web"), and "search_query" (a concise English search string).
- Use "youtube" for video tutorials, lectures, walkthroughs. Use "web" for documentation, articles,
  textbooks, official docs, or deep reads.
- "search_query" must be something a student can paste into YouTube or Google search — do NOT invent
  specific video IDs, channel URLs, or article URLs. Never output youtube.com/watch links.
- Spread suggestions across topics visible in the notes when possible.
- At least 2 items should use destination "youtube" and at least 2 should use "web".

Return JSON matching this exact schema:
{{
  "items": [
    {{
      "title": "string",
      "rationale": "string",
      "destination": "youtube",
      "search_query": "string"
    }}
  ]
}}

Return between {_RESOURCE_MIN} and {_RESOURCE_MAX} items (inclusive).
"""


def generate_learning_resources(
    *,
    class_title: str,
    note_segments: list[tuple[str, str]],
) -> tuple[list[LearningResourceItem], str]:
    if not note_segments:
        raise LearningResourcesError("No note content to generate resources from")
    settings = get_settings()
    if not settings.google_api_key:
        raise LearningResourcesError("GOOGLE_API_KEY is not configured")

    model_name = settings.google_model
    client = genai.Client(api_key=settings.google_api_key)
    prompt = _build_prompt(class_title=class_title, note_segments=note_segments)

    raw = ""
    try:
        resp = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.55,
                response_mime_type="application/json",
            ),
        )
        raw = resp.text or ""
        logger.info(
            "learning_resources_llm_response model=%s chars=%s preview=%r",
            model_name,
            len(raw),
            raw[:300],
        )
        data = json.loads(raw)
        if isinstance(data, list):
            data = {"items": data}
        parsed = LearningResourcesAI.model_validate(data)
        return list(parsed.items), model_name
    except (json.JSONDecodeError, ValidationError) as e:
        preview = raw[:500]
        logger.warning(
            "learning_resources_parse_failed err=%s preview=%r",
            e.__class__.__name__,
            preview,
        )
        raise LearningResourcesError(
            "Model did not return valid learning resources JSON"
        ) from e
    except ResourceExhausted as e:
        retry_after = _parse_retry_after_seconds(str(e))
        logger.info("learning_resources_rate_limited retry_after=%s", retry_after)
        if retry_after is not None:
            raise LearningResourcesRateLimitError(
                f"Rate limited by Gemini API. Please retry in {retry_after}s.",
                retry_after_seconds=retry_after,
            ) from e
        raise LearningResourcesRateLimitError(
            "Rate limited by Gemini API. Please retry shortly.",
            retry_after_seconds=None,
        ) from e
    except LearningResourcesError:
        raise
    except Exception as e:
        logger.exception(
            "learning_resources_generation_failed err=%s", e.__class__.__name__
        )
        raise LearningResourcesError(
            f"Learning resources generation failed ({e.__class__.__name__})"
        ) from e
