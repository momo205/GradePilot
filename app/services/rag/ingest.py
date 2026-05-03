from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db import crud
from app.db.models import DocumentChunk
from app.services.pdf_text import extract_text_from_pdf_bytes
from app.services.rag.chunking import TextChunk, chunk_text
from app.services.rag.embeddings import embed_documents


@dataclass(frozen=True)
class IngestResult:
    document_id: uuid.UUID
    chunks_created: int


def _build_base_metadata(*, filename: str, document_type: str) -> dict[str, object]:
    return {"source_filename": filename, "document_type": document_type}


def ingest_pdf_bytes(
    *,
    db: Session,
    user_id: uuid.UUID,
    class_id: uuid.UUID,
    filename: str,
    pdf_bytes: bytes,
    document_type: str = "syllabus",
    title: str | None = None,
) -> IngestResult:
    raw_text = extract_text_from_pdf_bytes(pdf_bytes)
    return ingest_raw_text(
        db=db,
        user_id=user_id,
        class_id=class_id,
        filename=filename,
        raw_text=raw_text,
        document_type=document_type,
        title=title,
    )


def ingest_raw_text(
    *,
    db: Session,
    user_id: uuid.UUID,
    class_id: uuid.UUID,
    filename: str,
    raw_text: str,
    document_type: str,
    title: str | None = None,
) -> IngestResult:
    doc = crud.create_document(
        db=db,
        user_id=user_id,
        class_id=class_id,
        filename=filename,
        title=title,
        document_type=document_type,
        raw_text=raw_text,
        metadata_json={},
    )

    base_meta = _build_base_metadata(filename=filename, document_type=document_type)
    chunks: list[TextChunk] = chunk_text(raw_text=raw_text, base_metadata=base_meta)
    if not chunks:
        return IngestResult(document_id=doc.id, chunks_created=0)

    vectors = embed_documents(texts=[c.text for c in chunks])

    chunk_rows: list[DocumentChunk] = []
    for c, v in zip(chunks, vectors, strict=True):
        chunk_rows.append(
            DocumentChunk(
                document_id=doc.id,
                class_id=class_id,
                user_id=user_id,
                chunk_index=c.chunk_index,
                chunk_text=c.text,
                embedding=v,
                metadata_json={**c.metadata},
            )
        )

    created = crud.bulk_create_document_chunks(db=db, chunks=chunk_rows)
    return IngestResult(document_id=doc.id, chunks_created=created)
