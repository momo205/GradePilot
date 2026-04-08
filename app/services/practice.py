from __future__ import annotations

import json
import logging
from typing import Any, cast

import google.generativeai as genai
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas import PracticeQuestionsAI

logger = logging.getLogger("gradepilot.ai")


class PracticeGenerationError(RuntimeError):
    pass


def _build_prompt(*, class_title: str, topic: str, count: int, difficulty: str) -> str:
    return f"""You are an expert computer science professor and study coach.

Generate exactly {count} practice questions for the topic "{topic}" in the course "{class_title}".
Difficulty level: {difficulty}

Rules:
- Questions must be specific, relevant, and academically rigorous for a CS course.
- Easy: definitions, basic concepts, simple recall.
- Medium: application, comparison, explain how/why.
- Hard: analysis, tradeoffs, complex problem-solving, edge cases.
- Answers must be clear, concise, and correct.
- Return ONLY valid JSON, no markdown, no extra text.

Return JSON matching this exact schema:
{{
  "questions": [
    {{"q": "question text", "a": "answer text"}},
    ...
  ]
}}

Generate exactly {count} questions.
"""


def generate_practice_questions(
    *, class_title: str, topic: str, count: int, difficulty: str
) -> list[dict[str, Any]]:
    settings = get_settings()
    if not settings.google_api_key:
        raise PracticeGenerationError("GOOGLE_API_KEY is not configured")

    genai_any = cast(Any, genai)
    genai_any.configure(api_key=settings.google_api_key)
    model_name = settings.google_model.removeprefix("models/")
    model = genai_any.GenerativeModel(model_name)
    prompt = _build_prompt(class_title=class_title, topic=topic, count=count, difficulty=difficulty)

    try:
        resp = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.6,
                "response_mime_type": "application/json",
            },
        )
        raw = resp.text or ""
        logger.info("practice_llm_response model=%s chars=%s preview=%r", model_name, len(raw), raw[:300])
        data = json.loads(raw)
        # Handle both {"questions": [...]} and direct list [...]
        if isinstance(data, list):
            data = {"questions": data}
        parsed = PracticeQuestionsAI.model_validate(data)
        return [q.model_dump() for q in parsed.questions]
    except (json.JSONDecodeError, ValidationError) as e:
        preview = raw[:500] if "raw" in locals() else ""
        logger.warning("practice_parse_failed err=%s preview=%r", e.__class__.__name__, preview)
        raise PracticeGenerationError("Model did not return valid questions JSON") from e
    except Exception as e:
        logger.exception("practice_generation_failed err=%s", e.__class__.__name__)
        raise PracticeGenerationError(f"Practice generation failed ({e.__class__.__name__})") from e
