from __future__ import annotations

import json
import logging
import re
import uuid

from google.api_core.exceptions import ResourceExhausted
from google import genai
from google.genai import types
from google.genai.errors import ClientError
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


class RagCitationVerificationError(RagAnswerError):
    """Returned JSON cited chunks that do not match retrieved text or ids."""


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


_SNIPPET_MAX_CHARS = 240


def _normalize_for_citation_match(text: str) -> str:
    """Collapse whitespace, case-fold, and map common unicode quotes for substring checks."""
    # PDFs / models often use curly quotes; chunk text may use ASCII.
    trans = str.maketrans(
        {
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u00a0": " ",
        }
    )
    folded = text.translate(trans)
    return " ".join(folded.split()).casefold()


def verify_rag_sources(
    *, sources: list[RagSourceOut], chunks: list[RetrievedChunk]
) -> list[RagSourceOut]:
    """Keep only sources that map to a retrieved chunk and whose snippet appears in chunk text.

    Deduplicates by (document_id, chunk_index), first verified occurrence wins.
    Raises RagAnswerError if the model supplied no sources or none could be verified.
    """
    if not sources:
        raise RagAnswerError(
            "Model returned no sources; citations are required for RAG answers."
        )

    allow: dict[tuple[str, int], RetrievedChunk] = {
        (str(c.document_id), c.chunk_index): c for c in chunks
    }
    seen_keys: set[tuple[str, int]] = set()
    verified: list[RagSourceOut] = []

    for src in sources:
        try:
            doc_uuid = uuid.UUID(str(src.document_id).strip())
        except ValueError:
            continue
        key = (str(doc_uuid), int(src.chunk_index))
        chunk = allow.get(key)
        if chunk is None:
            continue
        if key in seen_keys:
            continue

        norm_snip = _normalize_for_citation_match(src.snippet)
        if not norm_snip:
            continue
        norm_chunk = _normalize_for_citation_match(chunk.chunk_text)
        if norm_snip not in norm_chunk:
            continue

        seen_keys.add(key)
        snippet_out = src.snippet.strip()
        if len(snippet_out) > _SNIPPET_MAX_CHARS:
            snippet_out = snippet_out[:_SNIPPET_MAX_CHARS].rstrip()

        verified.append(
            RagSourceOut(
                document_id=str(chunk.document_id),
                filename=chunk.filename,
                document_type=chunk.document_type,
                chunk_index=chunk.chunk_index,
                snippet=snippet_out,
            )
        )

    if not verified:
        logger.warning(
            "rag_answer_citations_unverified model_sources=%s chunks=%s",
            len(sources),
            len(chunks),
        )
        raise RagCitationVerificationError(
            "Model citations could not be verified against retrieved materials."
        )
    return verified


_CITATION_REMINDER = """
CRITICAL — Your last answer failed citation checks. Fix this response:
- Copy document_id and chunk_index EXACTLY from the [S…] line above each source (do not invent UUIDs).
- Each snippet must be copied character-for-character from that source's body (you may only change outer whitespace); max ~240 chars.
"""


def _build_prompt(*, question: str, chunks: list[RetrievedChunk]) -> str:
    sources_text: list[str] = []
    for i, c in enumerate(chunks, start=1):
        snippet = c.chunk_text.strip()
        if len(snippet) > 1200:
            snippet = snippet[:1200].rstrip() + "…"
        sources_text.append(
            f"[S{i}] document_id={c.document_id} filename={c.filename} "
            f"type={c.document_type} chunk_index={c.chunk_index}\n{snippet}"
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
- For each source you cite, copy document_id and chunk_index EXACTLY from the [S…] header
  line for that body text (same line as "document_id=" and "chunk_index=").
- snippet must be a verbatim excerpt from that source's body below the header (aside from
  leading/trailing whitespace); max ~{_SNIPPET_MAX_CHARS} chars.
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

    base_prompt = _build_prompt(question=question, chunks=chunks)
    prompt = base_prompt
    raw = ""
    try:
        for attempt in range(2):
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
                "rag_answer_llm_response model=%s chars=%s attempt=%s",
                model_name,
                len(raw),
                attempt,
            )
            data = json.loads(raw)
            parsed = RagAnswerOut.model_validate(data)
            try:
                verified_sources = verify_rag_sources(
                    sources=parsed.sources, chunks=chunks
                )
            except RagCitationVerificationError:
                if attempt == 0:
                    logger.warning(
                        "rag_answer_citation_retry question_chars=%s chunks=%s",
                        len(question),
                        len(chunks),
                    )
                    prompt = base_prompt + _CITATION_REMINDER
                    continue
                raise
            return RagAnswerOut(answer=parsed.answer, sources=verified_sources)
        assert False, "rag answer loop should return or raise"
    except RagAnswerError:
        raise
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
    except ClientError as e:
        code = int(getattr(e, "code", 500) or 500)
        if code == 429:
            retry_after = _parse_retry_after_seconds(str(e))
            raise RagAnswerRateLimitError(
                "Rate limited by Gemini API (quota or requests per minute). "
                "Please retry shortly or check billing / limits at https://ai.google.dev/gemini-api/docs/rate-limits",
                retry_after_seconds=retry_after,
            ) from e
        detail = getattr(e, "message", None) or str(e)
        raise RagAnswerError(f"Gemini generate_content failed (HTTP {code}): {detail}") from e
    except Exception as e:  # noqa: BLE001
        logger.exception("rag_answer_failed err=%s", e.__class__.__name__)
        raise RagAnswerError(f"RAG answer failed ({e.__class__.__name__})") from e
