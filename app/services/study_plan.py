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
from app.schemas import StudyPlanAI
from app.services.gemini_rate_limit import (
    gemini_client_error_is_daily_quota,
    is_gemini_rate_limit_client_error,
    parse_retry_after_seconds_from_text,
    resource_exhausted_is_likely_daily_quota,
    retry_after_seconds_from_genai_client_error,
)

logger = logging.getLogger("gradepilot.ai")


class StudyPlanGenerationError(RuntimeError):
    pass


class StudyPlanRateLimitError(StudyPlanGenerationError):
    def __init__(self, message: str, *, retry_after_seconds: int | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def _build_prompt(
    *,
    class_title: str,
    notes_text: str,
    horizon_days: int,
    horizon_reason: str,
) -> str:
    return f"""You are an expert study coach.

Create a practical study plan for the course "{class_title}" based on the
student's notes. The plan must cover EXACTLY the next {horizon_days} day(s),
because that is how long the student has until {horizon_reason}.

Return ONLY valid JSON matching this schema:
{{
  "title": string,
  "goals": string[],
  "schedule": [{{ "day": string, "tasks": string[] }}]
}}

Constraints:
- The "schedule" array MUST contain exactly {horizon_days} item(s), one per
  calendar day starting today. Use the "day" field for human-readable labels
  like "Day 1 (Mon, May 11)" or just "Day 1".
- Distribute the notes' content evenly across those {horizon_days} day(s);
  do NOT pad with filler tasks if the horizon is short.
- Keep tasks concrete, specific to the notes, and actionable in a single
  study session.
- No markdown, no extra text outside JSON.

Student notes:
{notes_text}
"""


def generate_study_plan(
    *,
    class_title: str,
    notes_text: str,
    horizon_days: int = 14,
    horizon_reason: str = "the next checkpoint",
) -> tuple[dict[str, Any], str]:
    settings = get_settings()
    if settings.google_api_key is None or settings.google_api_key == "":
        raise StudyPlanGenerationError("GOOGLE_API_KEY is not configured")

    client = genai.Client(api_key=settings.google_api_key)
    model_name = settings.google_model
    horizon = max(1, min(int(horizon_days), 14))
    prompt = _build_prompt(
        class_title=class_title,
        notes_text=notes_text,
        horizon_days=horizon,
        horizon_reason=horizon_reason,
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
                    temperature=0.4,
                    response_mime_type="application/json",
                ),
            )
            raw = resp.text or ""
            logger.info(
                "study_plan_llm_response model=%s chars=%s",
                model_name,
                len(raw),
            )
            data = json.loads(raw)
            parsed = StudyPlanAI.model_validate(data)
            return parsed.model_dump(), model_name
        except (json.JSONDecodeError, ValidationError) as e:
            preview = raw[:500]
            logger.warning(
                "study_plan_parse_failed err=%s preview=%r",
                e.__class__.__name__,
                preview,
            )
            raise StudyPlanGenerationError(
                "Model did not return valid study-plan JSON"
            ) from e
        except ResourceExhausted as e:
            retry_after = parse_retry_after_seconds_from_text(str(e))
            logger.info("study_plan_rate_limited retry_after=%s", retry_after)
            if resource_exhausted_is_likely_daily_quota(e) or attempt >= max_retries:
                if retry_after is not None:
                    raise StudyPlanRateLimitError(
                        f"Rate limited by Gemini API. Please retry in {retry_after}s.",
                        retry_after_seconds=retry_after,
                    ) from e
                raise StudyPlanRateLimitError(
                    "Rate limited by Gemini API. Please retry shortly.",
                    retry_after_seconds=None,
                ) from e
            delay = retry_after or min(2 ** (attempt - 1), 45)
            sleep_s = min(delay, sleep_cap)
            logger.info(
                "study_plan_retry_resource_exhausted attempt=%s/%s sleep=%ss",
                attempt,
                max_retries,
                sleep_s,
            )
            time.sleep(sleep_s)
        except ClientError as e:
            if is_gemini_rate_limit_client_error(e):
                retry_after = retry_after_seconds_from_genai_client_error(e)
                logger.info(
                    "study_plan_rate_limited_genai code=%s retry_after=%s",
                    e.code,
                    retry_after,
                )
                if gemini_client_error_is_daily_quota(e) or attempt >= max_retries:
                    if retry_after is not None:
                        raise StudyPlanRateLimitError(
                            f"Gemini API quota or rate limit reached. Try again in about {retry_after}s.",
                            retry_after_seconds=retry_after,
                        ) from e
                    raise StudyPlanRateLimitError(
                        "Gemini API quota or rate limit reached. Please try again shortly.",
                        retry_after_seconds=None,
                    ) from e
                delay = retry_after or min(2 ** (attempt - 1), 45)
                sleep_s = min(delay, sleep_cap)
                logger.info(
                    "study_plan_retry_429 attempt=%s/%s sleep=%ss",
                    attempt,
                    max_retries,
                    sleep_s,
                )
                time.sleep(sleep_s)
                continue
            logger.warning(
                "study_plan_genai_client_error code=%s message=%s",
                e.code,
                (e.message or "")[:200],
            )
            raise StudyPlanGenerationError(
                (e.message or f"Gemini API error ({e.code})")[:800]
            ) from e
        except Exception as e:  # noqa: BLE001
            logger.exception(
                "study_plan_generation_failed err=%s", e.__class__.__name__
            )
            raise StudyPlanGenerationError(
                f"Study plan generation failed ({e.__class__.__name__})"
            ) from e
