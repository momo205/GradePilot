from __future__ import annotations

import json
import logging
import re

from google.api_core.exceptions import ResourceExhausted
from google import genai
from google.genai import types
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas import PracticeQuestion, PracticeQuestionsAI

logger = logging.getLogger("gradepilot.ai")


class PracticeGenerationError(RuntimeError):
    pass


class PracticeRateLimitError(PracticeGenerationError):
    def __init__(self, message: str, *, retry_after_seconds: int | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


_RETRY_RE = re.compile(r"Please retry in\s+([0-9]+(?:\.[0-9]+)?)s", re.IGNORECASE)


def _parse_retry_after_seconds(msg: str) -> int | None:
    m = _RETRY_RE.search(msg or "")
    if not m:
        return None
    try:
        return max(1, int(float(m.group(1)) + 0.999))
    except Exception:
        return None


def _format_note_segments(note_segments: list[tuple[str, str]]) -> str:
    parts: list[str] = []
    for label, text in note_segments:
        parts.append(f"### {label}\n{text.strip()}")
    return "\n\n".join(parts)


def _build_prompt_from_notes(
    *,
    class_title: str,
    note_segments: list[tuple[str, str]],
    count: int,
    difficulty: str,
) -> str:
    labels = [lbl for lbl, _ in note_segments]
    labels_csv = ", ".join(f'"{lbl}"' for lbl in labels)
    material = _format_note_segments(note_segments)
    return f"""You are an expert computer science professor and study coach.

Course: "{class_title}"

Below are the student's saved lecture notes. Each section is labeled (e.g. Lecture 1, Lecture 2).
Notes may be incomplete; only ask about concepts that appear in the notes.

--- BEGIN NOTES ---
{material}
--- END NOTES ---

Generate exactly {count} practice questions using ONLY the notes above.
Difficulty level: {difficulty}

Rules:
- Every question must be answerable from exactly one labeled section. Set "source_label" to that section's label, and it MUST be one of: {labels_csv}
- Spread questions across sections when there are multiple lectures (roughly proportional to how much material each section has). If there is only one section, all questions come from it.
- Easy: definitions, basic concepts, simple recall.
- Medium: application, comparison, explain how/why.
- Hard: analysis, tradeoffs, complex problem-solving, edge cases.
- Answers must be clear, concise, and correct from the notes.
- Return ONLY valid JSON, no markdown, no extra text.

Return JSON matching this exact schema:
{{
  "questions": [
    {{"q": "question text", "a": "answer text", "source_label": "Lecture 1"}},
    ...
  ]
}}

Generate exactly {count} questions.
"""


def generate_practice_questions(
    *,
    class_title: str,
    note_segments: list[tuple[str, str]],
    count: int,
    difficulty: str,
) -> list[PracticeQuestion]:
    if not note_segments:
        raise PracticeGenerationError("No note content to generate questions from")
    settings = get_settings()
    if not settings.google_api_key:
        raise PracticeGenerationError("GOOGLE_API_KEY is not configured")

    client = genai.Client(api_key=settings.google_api_key)
    model_name = settings.google_model
    prompt = _build_prompt_from_notes(
        class_title=class_title,
        note_segments=note_segments,
        count=count,
        difficulty=difficulty,
    )

    raw = ""
    try:
        resp = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.6,
                response_mime_type="application/json",
            ),
        )
        raw = resp.text or ""
        logger.info(
            "practice_llm_response model=%s chars=%s preview=%r",
            model_name,
            len(raw),
            raw[:300],
        )
        data = json.loads(raw)
        # Handle both {"questions": [...]} and direct list [...]
        if isinstance(data, list):
            data = {"questions": data}
        parsed = PracticeQuestionsAI.model_validate(data)
        return parsed.questions
    except (json.JSONDecodeError, ValidationError) as e:
        preview = raw[:500]
        logger.warning(
            "practice_parse_failed err=%s preview=%r",
            e.__class__.__name__,
            preview,
        )
        raise PracticeGenerationError(
            "Model did not return valid questions JSON"
        ) from e
    except ResourceExhausted as e:
        retry_after = _parse_retry_after_seconds(str(e))
        logger.info("practice_rate_limited retry_after=%s", retry_after)
        if retry_after is not None:
            raise PracticeRateLimitError(
                f"Rate limited by Gemini API. Please retry in {retry_after}s.",
                retry_after_seconds=retry_after,
            ) from e
        raise PracticeRateLimitError(
            "Rate limited by Gemini API. Please retry shortly.",
            retry_after_seconds=None,
        ) from e
    except Exception as e:
        logger.exception("practice_generation_failed err=%s", e.__class__.__name__)
        raise PracticeGenerationError(
            f"Practice generation failed ({e.__class__.__name__})"
        ) from e
