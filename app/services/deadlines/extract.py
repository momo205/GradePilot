from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime

from google.api_core.exceptions import ResourceExhausted
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from app.core.config import get_settings

logger = logging.getLogger("gradepilot.ai")


class DeadlineExtractError(RuntimeError):
    pass


class DeadlineExtractRateLimitError(DeadlineExtractError):
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


def _parse_due_at(value: str | None) -> datetime | None:
    if value is None:
        return None
    v = value.strip()
    if v == "":
        return None
    # Allow Z suffix
    v = v.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(v)
    except Exception:
        return None


class ExtractedDeadlineAI(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due_text: str = Field(min_length=1, max_length=500)
    due_at: str | None = None  # ISO 8601 if available
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    source_quote: str | None = Field(default=None, max_length=400)


class ExtractDeadlinesAI(BaseModel):
    deadlines: list[ExtractedDeadlineAI]


@dataclass(frozen=True)
class ExtractedDeadline:
    title: str
    due_text: str
    due_at: datetime | None
    confidence: float
    source_quote: str | None


def extract_deadlines_from_text(
    *, filename: str, raw_text: str
) -> list[ExtractedDeadline]:
    settings = get_settings()
    if not settings.google_api_key:
        raise DeadlineExtractError("GOOGLE_API_KEY is not configured")

    client = genai.Client(api_key=settings.google_api_key)
    model_name = settings.google_model

    prompt = f"""You are an academic assistant. Extract course deadlines from the document "{filename}".

Return ONLY valid JSON matching this exact schema:
{{
  "deadlines": [
    {{
      "title": "Assignment 1" ,
      "due_text": "Oct 5 11:59pm (from syllabus)",
      "due_at": "2026-10-05T23:59:00-04:00" ,
      "confidence": 0.0,
      "source_quote": "short quote from syllabus line(s)"
    }}
  ]
}}

Rules:
- Include exams, quizzes, assignments, labs, projects, presentations, and final exam.
- If there is no exact timestamp, omit due_at (null) but keep due_text.
- due_text must preserve what the syllabus says (do NOT invent).
- confidence should reflect how sure you are the item is a real deadline.
- No markdown, no extra keys, no extra text outside JSON.

Document content:
{raw_text[:12000]}
"""

    raw = ""
    try:
        resp = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )
        raw = resp.text or ""
        logger.info(
            "deadline_extract_llm_response model=%s chars=%s", model_name, len(raw)
        )
        data = json.loads(raw)
        parsed = ExtractDeadlinesAI.model_validate(data)
        out: list[ExtractedDeadline] = []
        for d in parsed.deadlines:
            out.append(
                ExtractedDeadline(
                    title=d.title.strip(),
                    due_text=d.due_text.strip(),
                    due_at=_parse_due_at(d.due_at),
                    confidence=float(d.confidence),
                    source_quote=(d.source_quote.strip() if d.source_quote else None),
                )
            )
        return out
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(
            "deadline_extract_parse_failed err=%s preview=%r",
            e.__class__.__name__,
            raw[:300],
        )
        raise DeadlineExtractError("Model did not return valid deadlines JSON") from e
    except ResourceExhausted as e:
        retry_after = _parse_retry_after_seconds(str(e))
        raise DeadlineExtractRateLimitError(
            "Rate limited by Gemini API. Please retry shortly.",
            retry_after_seconds=retry_after,
        ) from e
    except Exception as e:  # noqa: BLE001
        logger.exception("deadline_extract_failed err=%s", e.__class__.__name__)
        raise DeadlineExtractError(
            f"Deadline extraction failed ({e.__class__.__name__})"
        ) from e
