from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import crud
from app.db.session import get_db
from app.deps.auth import CurrentUser, get_current_user
from app.schemas import DeadlineImportOut
from app.services.google_calendar import (
    build_google_credentials_for_calendar,
    get_or_create_gradepilot_calendar,
    upsert_deadline_event,
)

router = APIRouter(prefix="/integrations/google", tags=["integrations"])


SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _user_uuid(user: CurrentUser) -> uuid.UUID:
    try:
        return uuid.UUID(user.user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user id")


@router.get("/oauth/start")
def google_oauth_start(
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, str]:
    _ = _user_uuid(user)
    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")
    if not settings.google_oauth_redirect_uri:
        raise HTTPException(status_code=503, detail="Missing GOOGLE_OAUTH_REDIRECT_URI")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_oauth_redirect_uri],
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.google_oauth_redirect_uri,
    )
    auth_url, _state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return {"authorization_url": auth_url}


@router.get("/oauth/callback")
def google_oauth_callback(
    code: str = Query(...),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    user_id = _user_uuid(user)
    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")
    if not settings.google_oauth_redirect_uri:
        raise HTTPException(status_code=503, detail="Missing GOOGLE_OAUTH_REDIRECT_URI")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_oauth_redirect_uri],
            }
        },
        scopes=SCOPES,
        redirect_uri=settings.google_oauth_redirect_uri,
    )
    try:
        flow.fetch_token(code=code)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=400, detail=f"OAuth exchange failed: {e}"
        ) from e

    creds = flow.credentials
    refresh_token = creds.refresh_token
    if not refresh_token:
        raise HTTPException(
            status_code=400,
            detail="No refresh token received. Try disconnecting the app and re-consenting.",
        )
    expiry: datetime | None = creds.expiry
    crud.upsert_google_integration(
        db=db,
        user_id=user_id,
        refresh_token=refresh_token,
        access_token=creds.token,
        token_expiry=expiry,
        scopes=" ".join(creds.scopes or []),
    )
    return {"ok": True}


@router.post("/calendar/sync/{class_id}")
def sync_class_to_google_calendar(
    class_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeadlineImportOut:
    user_id = _user_uuid(user)
    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")

    integ = crud.get_google_integration(db=db, user_id=user_id)
    if integ is None:
        raise HTTPException(status_code=400, detail="Google is not connected")

    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")

    creds = build_google_credentials_for_calendar(
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        access_token=integ.access_token,
        refresh_token=integ.refresh_token,
    )
    calendar_id = get_or_create_gradepilot_calendar(creds=creds)

    deadlines = crud.list_deadlines(db=db, user_id=user_id, class_id=class_id)
    created_or_updated = 0
    for d in deadlines:
        local_id = str(d.id)
        link = crud.get_calendar_event_link(
            db=db, user_id=user_id, kind="deadline", local_id=local_id
        )
        event_id = link.google_event_id if link is not None else None
        up = upsert_deadline_event(
            creds=creds,
            calendar_id=calendar_id,
            event_id=event_id,
            title=d.title,
            due_at=d.due_at,
            due_text=d.due_text,
        )
        crud.upsert_calendar_event_link(
            db=db,
            user_id=user_id,
            class_id=class_id,
            kind="deadline",
            local_id=local_id,
            google_calendar_id=up.calendar_id,
            google_event_id=up.event_id,
        )
        created_or_updated += 1

    return DeadlineImportOut(created=created_or_updated)
