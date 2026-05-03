from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.db import crud
from app.db.session import get_db
from app.deps.auth import CurrentUser, get_current_user
from app.schemas import ClassAskOut, ClassAskRequest, ClassAskSource, MaterialIngestOut
from app.services.rag.answer import (
    RagAnswerError,
    RagAnswerRateLimitError,
    generate_rag_answer,
)
from app.services.rag.embeddings import EmbeddingsError
from app.services.rag.ingest import ingest_pdf_bytes, ingest_raw_text
from app.services.rag.retrieve import retrieve_chunks

router = APIRouter(prefix="/classes", tags=["rag"])


def _user_uuid(user: CurrentUser) -> uuid.UUID:
    try:
        return uuid.UUID(user.user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user id")


@router.post("/{class_id}/materials", response_model=MaterialIngestOut)
async def upload_material(
    class_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    file: UploadFile | None = File(default=None),
    raw_text: str | None = Form(default=None),
    filename: str | None = Form(default=None),
    document_type: str = Form(default="syllabus"),
) -> MaterialIngestOut:
    user_id = _user_uuid(user)
    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")

    if file is None and (raw_text is None or raw_text.strip() == ""):
        raise HTTPException(status_code=400, detail="Provide file or raw_text")

    try:
        if file is not None:
            data = await file.read()
            if not data:
                raise HTTPException(status_code=400, detail="Empty upload")
            result = ingest_pdf_bytes(
                db=db,
                user_id=user_id,
                class_id=class_id,
                filename=file.filename or filename or "upload.pdf",
                pdf_bytes=data,
                document_type=document_type,
            )
            return MaterialIngestOut(
                document_id=result.document_id, chunks_created=result.chunks_created
            )

        result = ingest_raw_text(
            db=db,
            user_id=user_id,
            class_id=class_id,
            filename=filename or "notes.txt",
            raw_text=raw_text or "",
            document_type=document_type,
        )
        return MaterialIngestOut(
            document_id=result.document_id, chunks_created=result.chunks_created
        )
    except EmbeddingsError as e:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Embeddings failed: {e}. "
                "Check GOOGLE_EMBEDDING_MODEL (default models/gemini-embedding-001) and GOOGLE_API_KEY."
            ),
        ) from e
    except ProgrammingError as e:
        if "does not exist" in str(e.orig) if getattr(e, "orig", None) else str(e):
            raise HTTPException(
                status_code=503,
                detail=(
                    "RAG tables are missing in the database. Run the SQL in "
                    "docs/db/002_rag_documents.sql (Supabase SQL editor), then retry."
                ),
            ) from e
        raise


@router.post("/{class_id}/ask", response_model=ClassAskOut)
def ask_class(
    class_id: uuid.UUID,
    payload: ClassAskRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClassAskOut:
    user_id = _user_uuid(user)
    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")

    try:
        chunks = retrieve_chunks(
            db=db,
            user_id=user_id,
            class_id=class_id,
            question=payload.question,
            k=payload.top_k,
            document_type=payload.document_type,
        )
    except EmbeddingsError as e:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Embeddings failed: {e}. "
                "Check GOOGLE_EMBEDDING_MODEL (default models/gemini-embedding-001) and GOOGLE_API_KEY."
            ),
        ) from e
    if not chunks:
        return ClassAskOut(
            answer="I don't have enough information from the uploaded materials to answer that yet.",
            sources=[],
        )

    try:
        out = generate_rag_answer(question=payload.question, chunks=chunks)
    except RagAnswerRateLimitError as e:
        headers = {}
        if getattr(e, "retry_after_seconds", None):
            headers["Retry-After"] = str(e.retry_after_seconds)
        raise HTTPException(status_code=429, detail=str(e), headers=headers)
    except RagAnswerError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return ClassAskOut(
        answer=out.answer,
        sources=[
            ClassAskSource(
                document_id=s.document_id,
                filename=s.filename,
                document_type=s.document_type,
                chunk_index=s.chunk_index,
                snippet=s.snippet,
            )
            for s in out.sources
        ],
    )
