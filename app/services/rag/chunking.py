from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    text: str
    metadata: dict[str, object]


def _normalize_text(text: str) -> str:
    # Keep normalization minimal/deterministic; avoid heavy heuristics for MVP.
    return "\n".join(line.rstrip() for line in (text or "").splitlines()).strip()


def chunk_text(
    *,
    raw_text: str,
    max_chars: int = 3500,
    overlap_chars: int = 300,
    base_metadata: dict[str, object] | None = None,
) -> list[TextChunk]:
    """
    Deterministic, paragraph-aware chunking for RAG.

    - Uses character limits (fast, dependency-free).
    - Preserves small paragraphs; merges until max_chars.
    - Adds overlap to improve retrieval continuity.
    """
    if max_chars <= 200:
        raise ValueError("max_chars too small for meaningful chunks")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be >=0 and < max_chars")

    text = _normalize_text(raw_text)
    if text == "":
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() != ""]
    if not paragraphs:
        return []

    chunks: list[TextChunk] = []
    buf: list[str] = []
    buf_len = 0
    meta0 = dict(base_metadata or {})

    def flush() -> None:
        nonlocal buf, buf_len
        if not buf:
            return
        combined = "\n\n".join(buf).strip()
        if combined == "":
            buf = []
            buf_len = 0
            return
        idx = len(chunks)
        chunks.append(TextChunk(chunk_index=idx, text=combined, metadata=dict(meta0)))
        buf = []
        buf_len = 0

    for para in paragraphs:
        p = para
        # If a single paragraph is huge, hard-split it.
        while len(p) > max_chars:
            head = p[:max_chars]
            tail = p[max_chars:]
            if buf:
                flush()
            idx = len(chunks)
            chunks.append(TextChunk(chunk_index=idx, text=head, metadata=dict(meta0)))
            # overlap by characters for continuity
            p = (head[-overlap_chars:] if overlap_chars else "") + tail

        # If adding this paragraph would exceed budget, flush current buffer first.
        add_len = len(p) + (2 if buf else 0)
        if buf and (buf_len + add_len) > max_chars:
            flush()
            # carry overlap from previous chunk into next buffer
            if overlap_chars and chunks:
                prev = chunks[-1].text
                overlap = prev[-overlap_chars:].strip()
                if overlap:
                    buf = [overlap]
                    buf_len = len(overlap)

        if not buf:
            buf = [p]
            buf_len = len(p)
        else:
            buf.append(p)
            buf_len += 2 + len(p)

    flush()
    return chunks
