from __future__ import annotations

import uuid
import time
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

# In-memory store for PKCE verifier keyed by OAuth state.
# Keeps the auth flow working without adding persistence/migrations.
# Note: for multi-instance prod, replace with a shared store (DB/redis).
_OAUTH_STATE_TTL_S = 10 * 60
_oauth_state_to_verifier: dict[str, tuple[float, str]] = {}


def _oauth_store_put(*, state: str, code_verifier: str) -> None:
    now = time.time()
    _oauth_state_to_verifier[state] = (now + _OAUTH_STATE_TTL_S, code_verifier)
    # opportunistic cleanup
    expired = [k for k, (exp, _) in _oauth_state_to_verifier.items() if exp <= now]
    for k in expired:
        _oauth_state_to_verifier.pop(k, None)


def _oauth_store_pop(*, state: str) -> str | None:
    now = time.time()
    item = _oauth_state_to_verifier.pop(state, None)
    if item is None:
        return None
    exp, verifier = item
    if exp <= now:
        return None
    return verifier


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
        # Required for token exchange when PKCE is used.
        autogenerate_code_verifier=True,
    )
    auth_url, _state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    # Store PKCE verifier so the callback can exchange the code.
    code_verifier = getattr(flow, "code_verifier", None)
    if (
        isinstance(_state, str)
        and isinstance(code_verifier, str)
        and code_verifier != ""
    ):
        _oauth_store_put(state=_state, code_verifier=code_verifier)
    # Also return state+verifier so the frontend can keep it (more reliable than server memory).
    if (
        not isinstance(_state, str)
        or not isinstance(code_verifier, str)
        or code_verifier == ""
    ):
        return {"authorization_url": auth_url}
    return {
        "authorization_url": auth_url,
        "state": _state,
        "code_verifier": code_verifier,
    }


@router.get("/oauth/callback")
def google_oauth_callback(
    code: str = Query(...),
    state: str | None = Query(None),
    code_verifier: str | None = Query(None),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    user_id = _user_uuid(user)
    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")
    if not settings.google_oauth_redirect_uri:
        raise HTTPException(status_code=503, detail="Missing GOOGLE_OAUTH_REDIRECT_URI")

    verifier: str | None = None
    if code_verifier:
        verifier = code_verifier
    elif state:
        verifier = _oauth_store_pop(state=state)

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
    if verifier:
        # google-auth-oauthlib will include this in the token exchange (PKCE).
        setattr(flow, "code_verifier", verifier)
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
        if d.due_at is None:
            # Don't invent calendar times for text-only deadlines.
            continue
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


@router.get("/calendar")
def get_gradepilot_calendar_info(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Returns the GradePilot calendar id for the current user.

    Intended for embedding the calendar in the frontend.
    """
    user_id = _user_uuid(user)
    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")

    integ = crud.get_google_integration(db=db, user_id=user_id)
    if integ is None:
        raise HTTPException(status_code=400, detail="Google is not connected")

    creds = build_google_credentials_for_calendar(
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        access_token=integ.access_token,
        refresh_token=integ.refresh_token,
    )
    calendar_id = get_or_create_gradepilot_calendar(creds=creds)
    return {"calendar_id": calendar_id}
