from __future__ import annotations

import logging
import re
from typing import Any

from google.api_core.exceptions import ResourceExhausted
from google import genai
from google.genai import types

from app.core.config import get_settings

logger = logging.getLogger("gradepilot.ai")
_DEFAULT_EMBEDDING_DIM = 768


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
    client = genai.Client(api_key=settings.google_api_key)
    return client, settings.google_embedding_model


def embed_query(*, text: str) -> list[float]:
    client, model = _configure()
    try:
        resp = client.models.embed_content(
            model=model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=_DEFAULT_EMBEDDING_DIM,
            ),
        )
        emb = resp.embeddings[0].values if getattr(resp, "embeddings", None) else None
        if not isinstance(emb, list) or len(emb) == 0:
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
    client, model = _configure()
    if not texts:
        return []
    try:
        resp = client.models.embed_content(
            model=model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=_DEFAULT_EMBEDDING_DIM,
            ),
        )
        embeddings = getattr(resp, "embeddings", None)
        if not isinstance(embeddings, list) or not embeddings:
            raise EmbeddingsError("Embedding response missing 'embeddings'")
        out: list[list[float]] = []
        for e in embeddings:
            values = getattr(e, "values", None)
            if not isinstance(values, list) or len(values) == 0:
                raise EmbeddingsError("Embedding response missing 'values'")
            out.append([float(x) for x in values])
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
