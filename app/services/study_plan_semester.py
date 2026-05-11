from __future__ import annotations

import json
import logging
import time
from typing import Any

from google.api_core.exceptions import ResourceExhausted
from google import genai
from google.genai import types
from google.genai.errors import ClientError
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas import StudyPlanSemesterAI
from app.services.gemini_rate_limit import (
    gemini_client_error_is_daily_quota,
    is_gemini_rate_limit_client_error,
    parse_retry_after_seconds_from_text,
    resource_exhausted_is_likely_daily_quota,
    retry_after_seconds_from_genai_client_error,
)

logger = logging.getLogger("gradepilot.ai")


class SemesterStudyPlanGenerationError(RuntimeError):
    pass


class SemesterStudyPlanRateLimitError(SemesterStudyPlanGenerationError):
    def __init__(self, message: str, *, retry_after_seconds: int | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def _build_prompt(
    *,
    class_title: str,
    semester_start: str,
    semester_end: str,
    timezone: str,
    deadlines: list[dict[str, Any]],
    availability: list[dict[str, str]] | None,
) -> str:
    availability_text = json.dumps(availability or [], ensure_ascii=False)
    deadlines_text = json.dumps(deadlines, ensure_ascii=False)
    return f"""You are an expert study coach and semester planner.

Create a full-semester study plan for the course "{class_title}".

Inputs:
- Semester start: {semester_start}
- Semester end: {semester_end}
- Timezone: {timezone}
- Deadlines (JSON): {deadlines_text}
- Weekly availability blocks (JSON): {availability_text}

Return ONLY valid JSON matching this schema:
{{
  "title": string,
  "timezone": string,
  "semester_start": string,
  "semester_end": string,
  "weeks": [
    {{
      "week": number,
      "start": string,
      "end": string,
      "goals": string[],
      "tasks": [
        {{
          "title": string,
          "estimated_hours": number,
          "deadline_id": string | null
        }}
      ]
    }}
  ]
}}

Rules:
- Build weekly tasks that prepare for upcoming deadlines.
- deadline_id should reference an id from the input deadlines list when relevant.
- estimated_hours must be realistic (0.5 to 8 per task).
- Keep tasks concrete and actionable.
- Efficiency: include at most 20 entries in "weeks" (merge adjacent weeks if the
  semester is longer). Each week must have at most 3 goals and at most 5 tasks.
  Prefer shorter task titles; skip redundant micro-tasks.
- No markdown, no extra text outside JSON.
"""


def generate_semester_study_plan(
    *,
    class_title: str,
    semester_start: str,
    semester_end: str,
    timezone: str,
    deadlines: list[dict[str, Any]],
    availability: list[dict[str, str]] | None = None,
) -> tuple[dict[str, Any], str]:
    settings = get_settings()
    if not settings.google_api_key:
        raise SemesterStudyPlanGenerationError("GOOGLE_API_KEY is not configured")

    client = genai.Client(api_key=settings.google_api_key)
    model_name = settings.google_model
    prompt = _build_prompt(
        class_title=class_title,
        semester_start=semester_start,
        semester_end=semester_end,
        timezone=timezone,
        deadlines=deadlines,
        availability=availability,
    )

    max_retries = settings.gemini_max_retries
    sleep_cap = settings.gemini_retry_sleep_cap_seconds
    raw = ""
    attempt = 0
    while True:
        attempt += 1
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.35,
                    response_mime_type="application/json",
                ),
            )
            raw = resp.text or ""
            logger.info(
                "semester_plan_llm_response model=%s chars=%s",
                model_name,
                len(raw),
            )
            data = json.loads(raw)
            parsed = StudyPlanSemesterAI.model_validate(data)
            return parsed.model_dump(), model_name
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(
                "semester_plan_parse_failed err=%s preview=%r",
                e.__class__.__name__,
                raw[:300],
            )
            raise SemesterStudyPlanGenerationError(
                "Model did not return valid semester-plan JSON"
            ) from e
        except ResourceExhausted as e:
            retry_after = parse_retry_after_seconds_from_text(str(e))
            if resource_exhausted_is_likely_daily_quota(e) or attempt >= max_retries:
                if retry_after is not None:
                    raise SemesterStudyPlanRateLimitError(
                        f"Rate limited by Gemini API. Please retry in {retry_after}s.",
                        retry_after_seconds=retry_after,
                    ) from e
                raise SemesterStudyPlanRateLimitError(
                    "Rate limited by Gemini API. Please retry shortly.",
                    retry_after_seconds=None,
                ) from e
            delay = retry_after or min(2 ** (attempt - 1), 45)
            sleep_s = min(delay, sleep_cap)
            logger.info(
                "semester_plan_retry_resource_exhausted attempt=%s/%s sleep=%ss",
                attempt,
                max_retries,
                sleep_s,
            )
            time.sleep(sleep_s)
        except ClientError as e:
            if is_gemini_rate_limit_client_error(e):
                retry_after = retry_after_seconds_from_genai_client_error(e)
                logger.info(
                    "semester_plan_rate_limited_genai code=%s retry_after=%s",
                    e.code,
                    retry_after,
                )
                if gemini_client_error_is_daily_quota(e) or attempt >= max_retries:
                    if retry_after is not None:
                        raise SemesterStudyPlanRateLimitError(
                            "Gemini API quota or rate limit reached. "
                            f"Try again in about {retry_after}s, or check "
                            "https://ai.google.dev/gemini-api/docs/rate-limits",
                            retry_after_seconds=retry_after,
                        ) from e
                    raise SemesterStudyPlanRateLimitError(
                        "Gemini API quota or rate limit reached. "
                        "Please try again in a minute, or check "
                        "https://ai.google.dev/gemini-api/docs/rate-limits",
                        retry_after_seconds=None,
                    ) from e
                delay = retry_after or min(2 ** (attempt - 1), 45)
                sleep_s = min(delay, sleep_cap)
                logger.info(
                    "semester_plan_retry_429 attempt=%s/%s sleep=%ss",
                    attempt,
                    max_retries,
                    sleep_s,
                )
                time.sleep(sleep_s)
                continue
            logger.warning(
                "semester_plan_genai_client_error code=%s message=%s",
                e.code,
                (e.message or "")[:200],
            )
            raise SemesterStudyPlanGenerationError(
                (e.message or f"Gemini API error ({e.code})")[:800]
            ) from e
        except Exception as e:  # noqa: BLE001
            logger.exception("semester_plan_failed err=%s", e.__class__.__name__)
            raise SemesterStudyPlanGenerationError(
                f"Semester plan generation failed ({e.__class__.__name__})"
            ) from e
