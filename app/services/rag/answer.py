from __future__ import annotations

import json
import logging
import re

from google.api_core.exceptions import ResourceExhausted
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from app.core.config import get_settings
from app.services.rag.retrieve import RetrievedChunk

logger = logging.getLogger("gradepilot.ai")


class RagAnswerError(RuntimeError):
    pass


class RagAnswerRateLimitError(RagAnswerError):
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


class RagSourceOut(BaseModel):
    document_id: str
    filename: str
    document_type: str
    chunk_index: int
    snippet: str = Field(min_length=1)


class RagAnswerOut(BaseModel):
    answer: str = Field(min_length=1)
    sources: list[RagSourceOut]


def _build_prompt(*, question: str, chunks: list[RetrievedChunk]) -> str:
    sources_text: list[str] = []
    for i, c in enumerate(chunks, start=1):
        snippet = c.chunk_text.strip()
        if len(snippet) > 1200:
            snippet = snippet[:1200].rstrip() + "…"
        sources_text.append(
            f"[S{i}] filename={c.filename} type={c.document_type} chunk={c.chunk_index}\n{snippet}"
        )

    joined_sources = "\n\n".join(sources_text) if sources_text else "(no sources)"

    return f"""You are GradePilot, an academic assistant. Answer the student's question using ONLY the provided sources.

If the sources do not contain enough information, say you don't have enough information from the uploaded materials.

Return ONLY valid JSON matching this schema:
{{
  "answer": string,
  "sources": [
    {{"document_id": string, "filename": string, "document_type": string, "chunk_index": number, "snippet": string}}
  ]
}}

Rules:
- The answer must be grounded in sources.
- sources must include only the sources you actually used.
- snippet should be a short quote/summary (max ~240 chars) from that source.
- No markdown, no extra text.

Question:
{question}

Sources:
{joined_sources}
"""


def generate_rag_answer(*, question: str, chunks: list[RetrievedChunk]) -> RagAnswerOut:
    settings = get_settings()
    if not settings.google_api_key:
        raise RagAnswerError("GOOGLE_API_KEY is not configured")

    client = genai.Client(api_key=settings.google_api_key)
    model_name = settings.google_model

    prompt = _build_prompt(question=question, chunks=chunks)

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
        logger.info("rag_answer_llm_response model=%s chars=%s", model_name, len(raw))
        data = json.loads(raw)
        parsed = RagAnswerOut.model_validate(data)

        if not parsed.sources:
            parsed = RagAnswerOut(
                answer=parsed.answer,
                sources=[
                    RagSourceOut(
                        document_id=str(c.document_id),
                        filename=c.filename,
                        document_type=c.document_type,
                        chunk_index=c.chunk_index,
                        snippet=(c.chunk_text.strip()[:240] or "(empty)").strip(),
                    )
                    for c in chunks[:3]
                ],
            )
        return parsed
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(
            "rag_answer_parse_failed err=%s preview=%r", e.__class__.__name__, raw[:300]
        )
        raise RagAnswerError("Model did not return valid RAG JSON") from e
    except ResourceExhausted as e:
        retry_after = _parse_retry_after_seconds(str(e))
        raise RagAnswerRateLimitError(
            "Rate limited by Gemini API. Please retry shortly.",
            retry_after_seconds=retry_after,
        ) from e
    except Exception as e:  # noqa: BLE001
        logger.exception("rag_answer_failed err=%s", e.__class__.__name__)
        raise RagAnswerError(f"RAG answer failed ({e.__class__.__name__})") from e
