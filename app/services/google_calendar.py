from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, cast

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import crud
from app.db.models import Deadline, GoogleIntegration

logger = logging.getLogger("gradepilot.google_calendar")

CALENDAR_SUMMARY = "GradePilot"
CALENDAR_TIMEZONE = "UTC"

# OAuth scope contract.
#
# We request only `auth/calendar` (full read+write on calendars the user
# explicitly grants). Per Google's docs this scope is a strict superset of
# `auth/calendar.readonly`, so the freebusy.query reads in `list_busy_blocks`
# work without adding a second scope. Adding `.readonly` would force every
# existing user back through OAuth consent for zero functional benefit.
#
# `has_required_scopes` exists so that future scope additions (Drive, Tasks,
# etc.) can be detected and the user prompted to reconnect rather than the
# call failing opaquely.
REQUIRED_SCOPES: frozenset[str] = frozenset(
    {"https://www.googleapis.com/auth/calendar"}
)
SCOPES: list[str] = sorted(REQUIRED_SCOPES)


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
            scopes=list(SCOPES),
        ),
    )


def has_required_scopes(integration: GoogleIntegration) -> bool:
    """Return True iff the stored grant covers every scope GradePilot uses.

    Callers should treat False as "user must re-consent" rather than as a
    transient failure — the only fix is sending them back through OAuth.
    """
    granted = set((integration.scopes or "").split())
    return REQUIRED_SCOPES.issubset(granted)


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


def get_primary_calendar_id(*, creds: Credentials) -> str | None:
    """Return the user's primary Google calendar id (their account email).

    Used to overlay the user's personal calendar on top of the GradePilot
    calendar in the embedded view. Returns ``None`` if the API call fails or
    no entry is flagged as primary.
    """
    try:
        svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
        page_token: str | None = None
        while True:
            resp = svc.calendarList().list(pageToken=page_token).execute()
            for item in resp.get("items", []):
                if item.get("primary") is True:
                    raw_id = item.get("id")
                    return str(raw_id) if raw_id else None
            page_token = resp.get("nextPageToken")
            if not page_token:
                return None
    except Exception:  # noqa: BLE001
        return None


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


def create_study_session_event(
    *,
    db: Session,
    user_id: str,
    class_id: uuid.UUID,
    notes_id: uuid.UUID,
    title: str,
    start: datetime,
    end: datetime,
    description: str = "",
) -> dict[str, str]:
    """Create (or update) a study-session event on the GradePilot calendar.

    Idempotent on ``(user_id, kind='study_session', notes_id)``: if a link
    already exists the corresponding Google event is patched, otherwise a new
    event is inserted. This guards against duplicates if the replanner runs
    twice for the same ``notes_added`` trigger.

    Returns ``{"event_id": ..., "html_link": ...}``.

    Raises:
        ValueError: if ``start``/``end`` are naive or ``end <= start``.
        RuntimeError: if Google OAuth is not configured, the user has no
            integration, or the stored grant lacks the required scopes.
    """
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start and end must be timezone-aware")
    if end <= start:
        raise ValueError("end must be after start")

    user_uuid = uuid.UUID(user_id)

    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise RuntimeError("Google OAuth is not configured")

    integ = crud.get_google_integration(db=db, user_id=user_uuid)
    if integ is None:
        raise RuntimeError("Google integration not connected")
    if not has_required_scopes(integ):
        raise RuntimeError("Google integration is missing required scopes")

    creds = build_google_credentials_for_calendar(
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        access_token=integ.access_token,
        refresh_token=integ.refresh_token,
    )
    calendar_id = get_or_create_gradepilot_calendar(creds=creds)

    full_description = "Auto-scheduled by GradePilot.\n" f"Source notes: {notes_id}\n"
    if description:
        full_description += "\n" + description

    body: dict[str, Any] = {
        "summary": title,
        "description": full_description,
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
    }

    svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
    local_id = str(notes_id)
    existing_link = crud.get_calendar_event_link(
        db=db, user_id=user_uuid, kind="study_session", local_id=local_id
    )

    if existing_link is not None:
        event = (
            svc.events()
            .patch(
                calendarId=calendar_id,
                eventId=existing_link.google_event_id,
                body=body,
            )
            .execute()
        )
    else:
        event = svc.events().insert(calendarId=calendar_id, body=body).execute()

    event_id = str(event.get("id") or "")
    html_link = str(event.get("htmlLink") or "")

    crud.upsert_calendar_event_link(
        db=db,
        user_id=user_uuid,
        class_id=class_id,
        kind="study_session",
        local_id=local_id,
        google_calendar_id=calendar_id,
        google_event_id=event_id,
    )

    return {"event_id": event_id, "html_link": html_link}


def upsert_plan_day_event(
    *,
    db: Session,
    user_id: str,
    class_id: uuid.UUID,
    plan_id: uuid.UUID,
    day_index: int,
    title: str,
    start: datetime,
    end: datetime,
    description: str = "",
) -> dict[str, str]:
    """Create or update a calendar event for one day of a generated plan.

    Idempotent on ``(user_id, kind="plan_day_session", local_id=f"{plan_id}:{day_index}")``
    so re-running the replanner for the same plan never produces duplicate
    events; it patches the existing one in place. Generating a *new* plan
    yields a new ``plan_id`` so old events from the previous plan are simply
    left alone (the user can clear them in Google Calendar).

    Returns ``{"event_id": ..., "html_link": ...}``.

    Raises:
        ValueError: if ``start``/``end`` are naive or ``end <= start``.
        RuntimeError: if Google OAuth is not configured, the user has no
            integration, or the stored grant lacks the required scopes.
    """
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start and end must be timezone-aware")
    if end <= start:
        raise ValueError("end must be after start")
    if day_index < 0:
        raise ValueError("day_index must be non-negative")

    user_uuid = uuid.UUID(user_id)

    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise RuntimeError("Google OAuth is not configured")

    integ = crud.get_google_integration(db=db, user_id=user_uuid)
    if integ is None:
        raise RuntimeError("Google integration not connected")
    if not has_required_scopes(integ):
        raise RuntimeError("Google integration is missing required scopes")

    creds = build_google_credentials_for_calendar(
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        access_token=integ.access_token,
        refresh_token=integ.refresh_token,
    )
    calendar_id = get_or_create_gradepilot_calendar(creds=creds)

    full_description = (
        "Auto-scheduled by GradePilot.\n" f"Plan: {plan_id} (day {day_index + 1})\n"
    )
    if description:
        full_description += "\n" + description

    body: dict[str, Any] = {
        "summary": title,
        "description": full_description,
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
    }

    svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
    local_id = f"{plan_id}:{day_index}"
    existing_link = crud.get_calendar_event_link(
        db=db, user_id=user_uuid, kind="plan_day_session", local_id=local_id
    )

    if existing_link is not None:
        event = (
            svc.events()
            .patch(
                calendarId=calendar_id,
                eventId=existing_link.google_event_id,
                body=body,
            )
            .execute()
        )
    else:
        event = svc.events().insert(calendarId=calendar_id, body=body).execute()

    event_id = str(event.get("id") or "")
    html_link = str(event.get("htmlLink") or "")

    crud.upsert_calendar_event_link(
        db=db,
        user_id=user_uuid,
        class_id=class_id,
        kind="plan_day_session",
        local_id=local_id,
        google_calendar_id=calendar_id,
        google_event_id=event_id,
    )

    return {"event_id": event_id, "html_link": html_link}


def _merge_intervals(
    intervals: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    """Merge any overlapping/adjacent intervals. Inputs must be tz-aware."""
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda x: x[0])
    merged: list[tuple[datetime, datetime]] = [ordered[0]]
    for current_start, current_end in ordered[1:]:
        last_start, last_end = merged[-1]
        if current_start <= last_end:
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            merged.append((current_start, current_end))
    return merged


def list_busy_blocks(
    *,
    db: Session,
    user_id: str,
    start: datetime,
    end: datetime,
) -> list[tuple[datetime, datetime]]:
    """Return merged busy blocks from the user's primary Google calendar.

    Uses ``freebusy.query`` (not ``events.list``) — it is cheaper and Google
    returns exactly the busy intervals we need, already merged per-calendar.
    Returns an empty list (not an error) when:
      - the user has no Google integration connected
      - the stored grant doesn't cover the scopes we need (caller should
        prompt for reconnection separately, e.g. via ``has_required_scopes``)
      - the freebusy call returns an "errors" entry for the calendar

    Both ``start`` and ``end`` must be timezone-aware.
    """
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start and end must be timezone-aware")
    if end <= start:
        return []

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        return []

    integ = crud.get_google_integration(db=db, user_id=user_uuid)
    if integ is None:
        logger.info("list_busy_blocks: no google integration for user")
        return []
    if not has_required_scopes(integ):
        logger.info("list_busy_blocks: insufficient scopes; user must reconnect")
        return []

    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        logger.info("list_busy_blocks: google OAuth not configured")
        return []

    creds = build_google_credentials_for_calendar(
        client_id=settings.google_oauth_client_id,
        client_secret=settings.google_oauth_client_secret,
        access_token=integ.access_token,
        refresh_token=integ.refresh_token,
    )
    svc = build("calendar", "v3", credentials=creds, cache_discovery=False)

    body = {
        "timeMin": start.astimezone(timezone.utc).isoformat(),
        "timeMax": end.astimezone(timezone.utc).isoformat(),
        "items": [{"id": "primary"}],
    }
    resp = svc.freebusy().query(body=body).execute()
    calendars = resp.get("calendars") or {}
    primary = calendars.get("primary") or {}
    if primary.get("errors"):
        logger.info("list_busy_blocks: freebusy returned errors=%s", primary["errors"])
        return []

    raw_busy = primary.get("busy") or []
    intervals: list[tuple[datetime, datetime]] = []
    for entry in raw_busy:
        if not isinstance(entry, dict):
            continue
        s = entry.get("start")
        e = entry.get("end")
        if not isinstance(s, str) or not isinstance(e, str):
            continue
        try:
            s_dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            e_dt = datetime.fromisoformat(e.replace("Z", "+00:00"))
        except ValueError:
            continue
        if s_dt.tzinfo is None or e_dt.tzinfo is None:
            continue
        intervals.append((s_dt, e_dt))

    return _merge_intervals(intervals)
