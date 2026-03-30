from __future__ import annotations

import json
import logging
from typing import Any, cast

import google.generativeai as genai
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas import StudyPlanAI

logger = logging.getLogger("gradepilot.ai")


class StudyPlanGenerationError(RuntimeError):
    pass


def _build_prompt(*, class_title: str, notes_text: str) -> str:
    return f"""You are an expert study coach.

Create a practical study plan for the course "{class_title}" based on the student's notes.

Return ONLY valid JSON matching this schema:
{{
  "title": string,
  "goals": string[],
  "schedule": [{{ "day": string, "tasks": string[] }}]
}}

Constraints:
- Keep tasks concrete and actionable.
- Include 7-14 days in schedule depending on content density.
- No markdown, no extra text outside JSON.

Student notes:
{notes_text}
"""


def generate_study_plan(
    *, class_title: str, notes_text: str
) -> tuple[dict[str, Any], str]:
    settings = get_settings()
    if settings.google_api_key is None or settings.google_api_key == "":
        raise StudyPlanGenerationError("GOOGLE_API_KEY is not configured")

    genai_any = cast(Any, genai)
    genai_any.configure(api_key=settings.google_api_key)
    model_name = settings.google_model.removeprefix("models/")
    model = genai_any.GenerativeModel(model_name)
    prompt = _build_prompt(class_title=class_title, notes_text=notes_text)

    try:
        resp = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.4,
                "response_mime_type": "application/json",
            },
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
        preview = raw[:500] if "raw" in locals() else ""
        logger.warning(
            "study_plan_parse_failed err=%s preview=%r",
            e.__class__.__name__,
            preview,
        )
        raise StudyPlanGenerationError(
            "Model did not return valid study-plan JSON"
        ) from e
    except Exception as e:  # noqa: BLE001
        logger.exception("study_plan_generation_failed err=%s", e.__class__.__name__)
        raise StudyPlanGenerationError(
            f"Study plan generation failed ({e.__class__.__name__})"
        ) from e
