from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.services.rag.embeddings import embed_query


@dataclass(frozen=True)
class RetrievedChunk:
    document_id: uuid.UUID
    filename: str
    document_type: str
    chunk_index: int
    chunk_text: str
    score: float
    metadata: dict[str, object]


def retrieve_chunks(
    *,
    db: Session,
    user_id: uuid.UUID,
    class_id: uuid.UUID,
    question: str,
    k: int = 6,
    document_type: str | None = None,
) -> list[RetrievedChunk]:
    if k <= 0 or k > 20:
        raise ValueError("k must be between 1 and 20")

    qvec = embed_query(text=question)

    stmt = select(DocumentChunk, Document).join(
        Document, Document.id == DocumentChunk.document_id
    )
    stmt = stmt.where(
        DocumentChunk.user_id == user_id, DocumentChunk.class_id == class_id
    )
    if document_type:
        stmt = stmt.where(Document.document_type == document_type)

    distance_expr = None
    # pgvector operators only work on Postgres; SQLite tests store embeddings as JSON.
    if db.get_bind().dialect.name == "postgresql":
        distance_expr = DocumentChunk.embedding.cosine_distance(qvec).label("distance")
        stmt = stmt.add_columns(distance_expr).order_by(distance_expr.asc())
    else:
        stmt = stmt.order_by(DocumentChunk.chunk_index.asc())

    stmt = stmt.limit(k)

    results: list[RetrievedChunk] = []
    for row in db.execute(stmt).all():
        if distance_expr is not None:
            chunk, doc, dist = row
            score = 1.0 / (1.0 + float(dist or 0.0))
        else:
            chunk, doc = row
            score = 0.0
        results.append(
            RetrievedChunk(
                document_id=doc.id,
                filename=doc.filename,
                document_type=doc.document_type,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.chunk_text,
                score=score,
                metadata=dict(chunk.metadata_json or {}),
            )
        )
    return results
