from __future__ import annotations

import json
import logging
from typing import Any, cast

import google.generativeai as genai
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings

logger = logging.getLogger("gradepilot.ai")


class SummariseError(RuntimeError):
    pass


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

    genai_any = cast(Any, genai)
    genai_any.configure(api_key=settings.google_api_key)
    model_name = settings.google_model.removeprefix("models/")
    model = genai_any.GenerativeModel(model_name)

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
        resp = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,
                "response_mime_type": "application/json",
            },
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
    except Exception as e:
        logger.exception("summarise_failed err=%s", e.__class__.__name__)
        raise SummariseError(f"Summarisation failed ({e.__class__.__name__})") from e
