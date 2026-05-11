"""Unit tests for RAG citation verification (no LLM calls)."""

from __future__ import annotations

import uuid

import pytest

from app.services.rag.answer import RagAnswerError, RagSourceOut, verify_rag_sources
from app.services.rag.retrieve import RetrievedChunk


def _chunk(
    *,
    document_id: uuid.UUID | None = None,
    chunk_index: int = 0,
    text: str,
    filename: str = "notes.pdf",
    doc_type: str = "reading",
) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=document_id or uuid.uuid4(),
        filename=filename,
        document_type=doc_type,
        chunk_index=chunk_index,
        chunk_text=text,
        score=0.9,
        metadata={},
    )


def test_verify_accepts_verbatim_snippet_and_trusted_metadata() -> None:
    doc_id = uuid.uuid4()
    chunk = _chunk(
        document_id=doc_id,
        chunk_index=2,
        text="The midterm covers chapters one through three.",
        filename="syllabus.pdf",
        doc_type="syllabus",
    )
    out = verify_rag_sources(
        sources=[
            RagSourceOut(
                document_id=str(doc_id),
                filename="wrong.pdf",
                document_type="reading",
                chunk_index=2,
                snippet="chapters one through three",
            )
        ],
        chunks=[chunk],
    )
    assert len(out) == 1
    assert out[0].filename == "syllabus.pdf"
    assert out[0].document_type == "syllabus"
    assert out[0].chunk_index == 2
    assert out[0].document_id == str(doc_id)
    assert "chapters one through three" in out[0].snippet


def test_verify_whitespace_insensitive_match() -> None:
    doc_id = uuid.uuid4()
    chunk = _chunk(document_id=doc_id, text="Hello   world\n\tfoo")
    out = verify_rag_sources(
        sources=[
            RagSourceOut(
                document_id=str(doc_id),
                filename=chunk.filename,
                document_type=chunk.document_type,
                chunk_index=0,
                snippet="hello world foo",
            )
        ],
        chunks=[chunk],
    )
    assert len(out) == 1


def test_verify_case_insensitive_snippet() -> None:
    doc_id = uuid.uuid4()
    chunk = _chunk(document_id=doc_id, text="Python uses Indentation")
    out = verify_rag_sources(
        sources=[
            RagSourceOut(
                document_id=str(doc_id),
                filename=chunk.filename,
                document_type=chunk.document_type,
                chunk_index=0,
                snippet="indentation",
            )
        ],
        chunks=[chunk],
    )
    assert len(out) == 1


def test_verify_truncates_long_snippet() -> None:
    doc_id = uuid.uuid4()
    inner = "x" * 300
    chunk = _chunk(document_id=doc_id, text=f"start {inner} end")
    long_snip = "start " + "x" * 300
    out = verify_rag_sources(
        sources=[
            RagSourceOut(
                document_id=str(doc_id),
                filename=chunk.filename,
                document_type=chunk.document_type,
                chunk_index=0,
                snippet=long_snip,
            )
        ],
        chunks=[chunk],
    )
    assert len(out[0].snippet) <= 240


def test_verify_skips_malformed_document_id() -> None:
    chunk = _chunk(text="body text")
    with pytest.raises(RagAnswerError, match="could not be verified"):
        verify_rag_sources(
            sources=[
                RagSourceOut(
                    document_id="not-a-uuid",
                    filename=chunk.filename,
                    document_type=chunk.document_type,
                    chunk_index=0,
                    snippet="body text",
                )
            ],
            chunks=[chunk],
        )


def test_verify_drops_unknown_document_id() -> None:
    chunk = _chunk(text="only text")
    other_id = uuid.uuid4()
    with pytest.raises(RagAnswerError, match="could not be verified"):
        verify_rag_sources(
            sources=[
                RagSourceOut(
                    document_id=str(other_id),
                    filename=chunk.filename,
                    document_type=chunk.document_type,
                    chunk_index=0,
                    snippet="only text",
                )
            ],
            chunks=[chunk],
        )


def test_verify_drops_wrong_chunk_index() -> None:
    doc_id = uuid.uuid4()
    chunk = _chunk(document_id=doc_id, chunk_index=0, text="alpha")
    with pytest.raises(RagAnswerError, match="could not be verified"):
        verify_rag_sources(
            sources=[
                RagSourceOut(
                    document_id=str(doc_id),
                    filename=chunk.filename,
                    document_type=chunk.document_type,
                    chunk_index=99,
                    snippet="alpha",
                )
            ],
            chunks=[chunk],
        )


def test_verify_drops_non_substring_snippet() -> None:
    doc_id = uuid.uuid4()
    chunk = _chunk(document_id=doc_id, text="content in chunk")
    with pytest.raises(RagAnswerError, match="could not be verified"):
        verify_rag_sources(
            sources=[
                RagSourceOut(
                    document_id=str(doc_id),
                    filename=chunk.filename,
                    document_type=chunk.document_type,
                    chunk_index=0,
                    snippet="not in the chunk at all",
                )
            ],
            chunks=[chunk],
        )


def test_verify_deduplicates_by_document_and_chunk() -> None:
    doc_id = uuid.uuid4()
    chunk = _chunk(document_id=doc_id, text="repeat this phrase")
    out = verify_rag_sources(
        sources=[
            RagSourceOut(
                document_id=str(doc_id),
                filename=chunk.filename,
                document_type=chunk.document_type,
                chunk_index=0,
                snippet="repeat this",
            ),
            RagSourceOut(
                document_id=str(doc_id),
                filename=chunk.filename,
                document_type=chunk.document_type,
                chunk_index=0,
                snippet="this phrase",
            ),
        ],
        chunks=[chunk],
    )
    assert len(out) == 1
    assert "repeat this" in out[0].snippet


def test_verify_empty_sources_raises() -> None:
    chunk = _chunk(text="anything")
    with pytest.raises(RagAnswerError, match="no sources"):
        verify_rag_sources(sources=[], chunks=[chunk])


def test_verify_keeps_second_chunk_when_first_invalid() -> None:
    a = uuid.uuid4()
    b = uuid.uuid4()
    c0 = _chunk(document_id=a, chunk_index=0, text="skip me")
    c1 = _chunk(document_id=b, chunk_index=0, text="keep this part")
    out = verify_rag_sources(
        sources=[
            RagSourceOut(
                document_id=str(a),
                filename=c0.filename,
                document_type=c0.document_type,
                chunk_index=0,
                snippet="not in skip me",
            ),
            RagSourceOut(
                document_id=str(b),
                filename=c1.filename,
                document_type=c1.document_type,
                chunk_index=0,
                snippet="keep this part",
            ),
        ],
        chunks=[c0, c1],
    )
    assert len(out) == 1
    assert out[0].document_id == str(b)
