from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.db import crud
from app.db.models import Deadline

CALENDAR_SUMMARY = "GradePilot"
CALENDAR_TIMEZONE = "UTC"


@dataclass(frozen=True)
class CalendarEventUpsert:
    calendar_id: str
    event_id: str


def _build_credentials(
    *, access_token: str | None, refresh_token: str, client_id: str, client_secret: str
) -> Credentials:
    # googleapiclient will refresh automatically when expired if refresh_token present.
    # Some google-auth versions ship partial type info; avoid mypy's `no-untyped-call`
    # by explicitly calling it through `Any`.
    creds_ctor = cast(Any, Credentials)
    return cast(
        Credentials,
        creds_ctor(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/calendar"],
        ),
    )


def get_or_create_gradepilot_calendar(*, creds: Credentials) -> str:
    svc = build("calendar", "v3", credentials=creds, cache_discovery=False)

    page_token: str | None = None
    while True:
        resp = svc.calendarList().list(pageToken=page_token).execute()
        for item in resp.get("items", []):
            if item.get("summary") == CALENDAR_SUMMARY:
                return str(item.get("id"))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    created = (
        svc.calendars()
        .insert(body={"summary": CALENDAR_SUMMARY, "timeZone": CALENDAR_TIMEZONE})
        .execute()
    )
    return str(created.get("id"))


def upsert_deadline_event(
    *,
    creds: Credentials,
    calendar_id: str,
    event_id: str | None,
    title: str,
    due_at: datetime | None,
    due_text: str,
) -> CalendarEventUpsert:
    svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
    summary = f"Deadline: {title}"
    description = f"Imported by GradePilot.\n\nDue: {due_text}"

    if due_at is not None:
        dt = due_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Google Calendar requires a valid end time for timed events.
        # Represent deadlines as a short timed block.
        end_dt = dt + timedelta(minutes=15)
        body: dict[str, Any] = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": dt.isoformat()},
            "end": {"dateTime": end_dt.isoformat()},
        }
    else:
        # Google Calendar API requires start/end. If we don't have a real timestamp,
        # we can't reliably create an event without inventing a date.
        raise ValueError("Deadline has no due_at; cannot sync to Google Calendar")

    if event_id:
        updated = (
            svc.events()
            .patch(calendarId=calendar_id, eventId=event_id, body=body)
            .execute()
        )
        return CalendarEventUpsert(
            calendar_id=calendar_id, event_id=str(updated.get("id"))
        )

    created = svc.events().insert(calendarId=calendar_id, body=body).execute()
    return CalendarEventUpsert(calendar_id=calendar_id, event_id=str(created.get("id")))


def build_google_credentials_for_calendar(
    *,
    client_id: str,
    client_secret: str,
    access_token: str | None,
    refresh_token: str,
) -> Credentials:
    return _build_credentials(
        access_token=access_token,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
    )


def sync_class(
    *,
    db: Any,
    user_id: Any,
    class_id: Any,
    settings: Any,
) -> dict[str, Any]:
    """
    Sync a class's deadlines into the user's GradePilot Google Calendar.

    This is used by orchestration layers (e.g. LangGraph replanner) so they can
    reuse the same behavior as the integrations router.
    """
    if not getattr(settings, "google_oauth_client_id", None) or not getattr(
        settings, "google_oauth_client_secret", None
    ):
        raise RuntimeError("Google OAuth is not configured")

    integ = crud.get_google_integration(db=db, user_id=user_id)
    if integ is None:
        raise RuntimeError("Google integration not connected")

    creds = build_google_credentials_for_calendar(
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        access_token=integ.access_token,
        refresh_token=integ.refresh_token,
    )
    calendar_id = get_or_create_gradepilot_calendar(creds=creds)

    deadlines: list[Deadline] = crud.list_deadlines(
        db=db, user_id=user_id, class_id=class_id
    )
    created_or_updated = 0
    for d in deadlines:
        if d.due_at is None:
            # Skip unscheduled deadlines (only due_text). We avoid inventing dates.
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
    return {"created_or_updated": created_or_updated}
