from __future__ import annotations

import json
import logging
import re

from google.api_core.exceptions import ResourceExhausted
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings

logger = logging.getLogger("gradepilot.ai")


class SummariseError(RuntimeError):
    pass


class SummariseRateLimitError(SummariseError):
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


class SummaryResult(BaseModel):
    title: str
    summary: str
    key_topics: list[str]
    important_dates: list[str]
    extracted_notes: str


def summarise_document(*, filename: str, raw_text: str) -> SummaryResult:
    settings = get_settings()
    if not settings.google_api_key:
        raise SummariseError("GOOGLE_API_KEY is not configured")

    client = genai.Client(api_key=settings.google_api_key)
    model_name = settings.google_model

    prompt = f"""You are an expert academic assistant. A student has uploaded a document called "{filename}".

Analyse the document and extract the most useful academic information.

Return ONLY valid JSON matching this exact schema:
{{
  "title": "short descriptive title for this document",
  "summary": "2-3 sentence summary of what this document covers",
  "key_topics": ["topic 1", "topic 2", ...],
  "important_dates": ["any deadlines, exam dates, or due dates found, e.g. 'Midterm: Oct 15'"],
  "extracted_notes": "clean, well-structured notes extracted from the document, preserving all important content"
}}

Rules:
- key_topics: list the main subjects/concepts covered (max 8)
- important_dates: only include if actual dates/deadlines are present, otherwise empty list
- extracted_notes: rewrite the content as clean study notes, removing boilerplate/headers
- Return ONLY valid JSON, no markdown, no extra text

Document content:
{raw_text[:8000]}
"""

    raw = ""
    try:
        resp = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                response_mime_type="application/json",
            ),
        )
        raw = resp.text or ""
        logger.info("summarise_llm_response model=%s chars=%s", model_name, len(raw))
        data = json.loads(raw)
        return SummaryResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(
            "summarise_parse_failed err=%s preview=%r", e.__class__.__name__, raw[:300]
        )
        raise SummariseError("Model did not return valid summary JSON") from e
    except ResourceExhausted as e:
        # Gemini quota/rate-limit. Surface as 429 upstream (router maps this).
        retry_after = _parse_retry_after_seconds(str(e))
        logger.info("summarise_rate_limited retry_after=%s", retry_after)
        if retry_after is not None:
            raise SummariseRateLimitError(
                f"Rate limited by Gemini API. Please retry in {retry_after}s.",
                retry_after_seconds=retry_after,
            ) from e
        raise SummariseRateLimitError(
            "Rate limited by Gemini API. Please retry shortly.",
            retry_after_seconds=None,
        ) from e
    except Exception as e:
        logger.exception("summarise_failed err=%s", e.__class__.__name__)
        raise SummariseError(f"Summarisation failed ({e.__class__.__name__})") from e
