from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, cast

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

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
        body: dict[str, Any] = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": dt.isoformat()},
            "end": {"dateTime": dt.isoformat()},
        }
    else:
        # Best-effort all-day event without inventing dates.
        body = {
            "summary": summary,
            "description": description,
        }

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
