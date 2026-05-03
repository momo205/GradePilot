from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.deps.auth import CurrentUser, get_current_user
from app.schemas import ExtractPdfOut, SummariseOut, SummariseRequest
from app.services.pdf_text import extract_text_from_pdf_bytes
from app.services.summarise import (
    SummariseError,
    SummariseRateLimitError,
    summarise_document,
)

router = APIRouter(prefix="/summarise", tags=["summarise"])


@router.post("", response_model=SummariseOut)
def summarise_endpoint(
    payload: SummariseRequest,
    user: CurrentUser = Depends(get_current_user),
) -> SummariseOut:
    try:
        result = summarise_document(
            filename=payload.filename, raw_text=payload.raw_text
        )
    except SummariseRateLimitError as e:
        headers = {}
        if getattr(e, "retry_after_seconds", None):
            headers["Retry-After"] = str(e.retry_after_seconds)
        raise HTTPException(status_code=429, detail=str(e), headers=headers)
    except SummariseError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return SummariseOut(
        title=result.title,
        summary=result.summary,
        key_topics=result.key_topics,
        important_dates=result.important_dates,
        extracted_notes=result.extracted_notes,
    )


@router.post("/extract-pdf", response_model=ExtractPdfOut)
async def extract_pdf_endpoint(
    file: UploadFile = File(...),
    _user: CurrentUser = Depends(get_current_user),
) -> ExtractPdfOut:
    name = (file.filename or "").strip()
    if not name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Upload a .pdf file")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    try:
        raw_text = extract_text_from_pdf_bytes(data)
    except Exception as e:  # noqa: BLE001 — surface parse failures to client
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {e}") from e
    return ExtractPdfOut(filename=name, raw_text=raw_text)
