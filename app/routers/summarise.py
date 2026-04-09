from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.deps.auth import CurrentUser, get_current_user
from app.schemas import SummariseOut, SummariseRequest
from app.services.summarise import SummariseError, summarise_document

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
    except SummariseError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return SummariseOut(
        title=result.title,
        summary=result.summary,
        key_topics=result.key_topics,
        important_dates=result.important_dates,
        extracted_notes=result.extracted_notes,
    )
