from __future__ import annotations

import logging
import re
from typing import Any, cast

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

from app.core.config import get_settings

logger = logging.getLogger("gradepilot.ai")


class EmbeddingsError(RuntimeError):
    pass


class EmbeddingsRateLimitError(EmbeddingsError):
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


def _configure() -> tuple[Any, str]:
    settings = get_settings()
    if not settings.google_api_key:
        raise EmbeddingsError("GOOGLE_API_KEY is not configured")
    genai_any = cast(Any, genai)
    genai_any.configure(api_key=settings.google_api_key)
    return genai_any, settings.google_embedding_model


def embed_query(*, text: str) -> list[float]:
    genai_any, model = _configure()
    try:
        resp = genai_any.embed_content(
            model=model,
            content=text,
            task_type="RETRIEVAL_QUERY",
        )
        emb = resp.get("embedding")
        if not isinstance(emb, list) or not emb:
            raise EmbeddingsError("Embedding response missing 'embedding'")
        return [float(x) for x in emb]
    except ResourceExhausted as e:
        retry_after = _parse_retry_after_seconds(str(e))
        raise EmbeddingsRateLimitError(
            "Rate limited by Gemini embeddings API. Please retry shortly.",
            retry_after_seconds=retry_after,
        ) from e
    except Exception as e:  # noqa: BLE001
        logger.exception("embed_query_failed err=%s", e.__class__.__name__)
        raise EmbeddingsError(f"Embedding failed ({e.__class__.__name__})") from e


def embed_documents(*, texts: list[str]) -> list[list[float]]:
    genai_any, model = _configure()
    if not texts:
        return []
    out: list[list[float]] = []
    try:
        for t in texts:
            resp = genai_any.embed_content(
                model=model,
                content=t,
                task_type="RETRIEVAL_DOCUMENT",
            )
            emb = resp.get("embedding")
            if not isinstance(emb, list) or not emb:
                raise EmbeddingsError("Embedding response missing 'embedding'")
            out.append([float(x) for x in emb])
        return out
    except ResourceExhausted as e:
        retry_after = _parse_retry_after_seconds(str(e))
        raise EmbeddingsRateLimitError(
            "Rate limited by Gemini embeddings API. Please retry shortly.",
            retry_after_seconds=retry_after,
        ) from e
    except Exception as e:  # noqa: BLE001
        logger.exception("embed_documents_failed err=%s", e.__class__.__name__)
        raise EmbeddingsError(f"Embedding failed ({e.__class__.__name__})") from e

