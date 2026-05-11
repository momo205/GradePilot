from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass

from google.api_core.exceptions import ResourceExhausted
from google import genai
from google.genai.errors import ClientError
from google.genai import types
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import crud
from app.services.deadlines.extract import (
    DeadlineExtractError,
    DeadlineExtractPermissionError,
    DeadlineExtractRateLimitError,
    ExtractedDeadlineAI,
    _parse_due_at,
    _parse_retry_after_seconds,
)
from app.services.pdf_text import extract_text_from_pdf_bytes
from app.services.rag.ingest import ingest_raw_text

logger = logging.getLogger("gradepilot.ai")

_RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SyllabusBootstrapExtractAI(BaseModel):
    deadlines: list[ExtractedDeadlineAI] = Field(default_factory=list)
    course_summary: str = Field(
        default="",
        max_length=6000,
    )
    semester_timezone: str | None = Field(default=None, max_length=80)
    semester_start: str | None = Field(default=None, max_length=12)
    semester_end: str | None = Field(default=None, max_length=12)
    semester_term: str | None = Field(
        default=None,
        max_length=20,
        description="fall or spring if clear from the document, else null",
    )


@dataclass(frozen=True)
class SyllabusBootstrapResult:
    deadlines_created: int
    syllabus_chunks: int
    course_summary_chunks: int
    course_summary: str
    suggested_timezone: str | None
    suggested_semester_start: str | None
    suggested_semester_end: str | None
    suggested_semester_term: str | None


def extract_syllabus_bootstrap_ai(*, filename: str, raw_text: str) -> SyllabusBootstrapExtractAI:
    settings = get_settings()
    if not settings.google_api_key:
        raise DeadlineExtractError(
            "GOOGLE_API_KEY is not configured",
            status_code=503,
        )

    client = genai.Client(api_key=settings.google_api_key)
    model_name = settings.google_model
    snippet = (raw_text or "")[:16000]

    prompt = f"""You are an academic assistant analyzing "{filename}".

Return ONLY valid JSON matching this exact schema:
{{
  "deadlines": [
    {{
      "title": "Assignment 1",
      "due_text": "Oct 5 11:59pm",
      "due_at": "2026-10-05T23:59:00-04:00",
      "confidence": 0.85,
      "source_quote": "short quote"
    }}
  ],
  "course_summary": "3-8 sentences describing what the course covers, level, major themes, and assessment style. Written for a student study coach.",
  "semester_timezone": "IANA timezone if stated (e.g. America/New_York), else null",
  "semester_start": "YYYY-MM-DD first class or term start if stated, else null",
  "semester_end": "YYYY-MM-DD last class or finals week end if stated, else null",
  "semester_term": "fall or spring if the document clearly indicates (e.g. Fall 2026, Spring semester), else null"
}}

Rules:
- deadlines: exams, quizzes, assignments, projects, presentations, labs, final exam.
- If no exact timestamp for a deadline, set due_at to null but keep due_text verbatim from the document.
- course_summary must be grounded in the document; do not invent requirements not present.
- semester_* fields only when reasonably inferable; otherwise null.
- semester_term must be lowercase "fall", "spring", or null.
- No markdown, no extra keys, no text outside JSON.

Document content:
{snippet}
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
        data = json.loads(raw)
        return SyllabusBootstrapExtractAI.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(
            "syllabus_bootstrap_parse_failed err=%s preview=%r",
            e.__class__.__name__,
            raw[:300],
        )
        raise DeadlineExtractError(
            "Model did not return valid syllabus bootstrap JSON"
        ) from e
    except ResourceExhausted as e:
        retry_after = _parse_retry_after_seconds(str(e))
        raise DeadlineExtractRateLimitError(
            "Rate limited by Gemini API. Please retry shortly.",
            retry_after_seconds=retry_after,
        ) from e
    except ClientError as e:
        code = int(getattr(e, "code", 500) or 500)
        if code in (401, 403):
            raise DeadlineExtractPermissionError(
                "Gemini API access denied for this project/key. "
                "Verify the API key, project access/allowlist, and billing.",
                status_code=503,
            ) from e
        raise DeadlineExtractError(
            f"Gemini API request failed (HTTP {code})",
            status_code=502,
        ) from e
    except Exception as e:  # noqa: BLE001
        logger.exception("syllabus_bootstrap_failed err=%s", e.__class__.__name__)
        raise DeadlineExtractError(
            f"Syllabus processing failed ({e.__class__.__name__})"
        ) from e


def _coerce_semester_term(raw: str | None) -> str | None:
    if not raw or not isinstance(raw, str):
        return None
    v = raw.strip().lower()
    if v in ("fall", "autumn"):
        return "fall"
    if v == "spring":
        return "spring"
    return None


def _infer_term_from_start_date(start: str | None) -> str | None:
    if not start or not _RE_DATE.match(start):
        return None
    try:
        month = int(start[5:7])
    except (ValueError, IndexError):
        return None
    if 8 <= month <= 12:
        return "fall"
    if 1 <= month <= 6:
        return "spring"
    return None


def _coerce_timeline_dates(
    tz: str | None, start: str | None, end: str | None
) -> tuple[str | None, str | None, str | None]:
    out_tz = tz.strip() if isinstance(tz, str) and tz.strip() else None
    out_s = start.strip() if isinstance(start, str) and start.strip() else None
    out_e = end.strip() if isinstance(end, str) and end.strip() else None
    if out_s and not _RE_DATE.match(out_s):
        out_s = None
    if out_e and not _RE_DATE.match(out_e):
        out_e = None
    return out_tz, out_s, out_e


def run_onboarding_syllabus_bootstrap(
    *,
    db: Session,
    user_id: uuid.UUID,
    class_id: uuid.UUID,
    filename: str,
    pdf_bytes: bytes,
) -> SyllabusBootstrapResult:
    raw_text = extract_text_from_pdf_bytes(pdf_bytes)
    if not raw_text.strip():
        raise DeadlineExtractError(
            "No extractable text found in this PDF. Try a text-based PDF or paste content instead.",
            status_code=400,
        )

    parsed = extract_syllabus_bootstrap_ai(filename=filename, raw_text=raw_text)

    sug_tz, sug_start, sug_end = _coerce_timeline_dates(
        parsed.semester_timezone,
        parsed.semester_start,
        parsed.semester_end,
    )
    sug_term = _coerce_semester_term(parsed.semester_term)
    if sug_term is None:
        sug_term = _infer_term_from_start_date(sug_start)

    syllabus_ingest = ingest_raw_text(
        db=db,
        user_id=user_id,
        class_id=class_id,
        filename=filename,
        raw_text=raw_text,
        document_type="syllabus",
        title=None,
    )

    summary = (parsed.course_summary or "").strip()
    summary_chunks = 0
    if summary:
        summary_ingest = ingest_raw_text(
            db=db,
            user_id=user_id,
            class_id=class_id,
            filename="course-summary.txt",
            raw_text=summary,
            document_type="course_summary",
            title="Course summary (from syllabus)",
        )
        summary_chunks = summary_ingest.chunks_created

    created = 0
    for d in parsed.deadlines:
        crud.create_deadline(
            db=db,
            user_id=user_id,
            class_id=class_id,
            title=d.title.strip(),
            due_text=d.due_text.strip(),
            due_at=_parse_due_at(d.due_at),
        )
        created += 1

    return SyllabusBootstrapResult(
        deadlines_created=created,
        syllabus_chunks=syllabus_ingest.chunks_created,
        course_summary_chunks=summary_chunks,
        course_summary=summary,
        suggested_timezone=sug_tz,
        suggested_semester_start=sug_start,
        suggested_semester_end=sug_end,
        suggested_semester_term=sug_term,
    )
