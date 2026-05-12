"""Multi-day study-session scheduling for a generated plan.

Given a freshly-persisted study plan, book one 60-minute calendar block per
day in the plan's schedule on the user's GradePilot calendar. Idempotent on
``(plan_id, day_index)`` via ``upsert_plan_day_event`` so each plan day keeps
its own event (re-runs patch in place instead of duplicating).

Pure failure semantics: per-day failures are returned in ``errors`` rather
than raised, mirroring the replanner-node contract so callers (the replanner
node and the ``POST /study-plan`` endpoint) can both surface partial results.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.db import crud
from app.services.google_calendar import (
    has_required_scopes,
    list_busy_blocks,
    upsert_plan_day_event,
)
from app.services.scheduling.slot_finder import find_first_available_slot

logger = logging.getLogger("gradepilot.plan_sessions")


def schedule_plan_day_sessions(
    *,
    db: Session,
    user_id: uuid.UUID,
    class_id: uuid.UUID,
    plan_id: uuid.UUID,
    plan_json: dict[str, Any],
    class_title: str,
    user_timezone: str,
    preferred_windows: list[dict[str, str]],
    now_utc: datetime | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Book a calendar event for each day in ``plan_json["schedule"]``.

    Returns ``(scheduled_sessions, errors)``. ``scheduled_sessions`` mirrors
    the replanner-state shape: one entry per day with ``day_index``,
    ``day_label``, ``tasks``, ``start``, ``end``, ``in_preferred_window``,
    ``calendar_event_link``, and ``calendar_event_id``. The list is empty if
    Google is not connected or the plan has no schedule items.

    ``errors`` is a list of stable, machine-parseable strings (e.g.
    ``"plan_sessions_skip:day=2:no_slot_found"``) intended for logging or
    surfacing to the user verbatim.

    Caller responsibilities:
    - The user must own ``user_id``/``class_id``/``plan_id``; this function
      does not re-check ownership.
    - ``now_utc`` defaults to ``datetime.now(timezone.utc)`` and exists for
      deterministic testing.
    """
    errors: list[str] = []

    schedule_items = plan_json.get("schedule")
    if not isinstance(schedule_items, list) or not schedule_items:
        return [], errors

    integ = crud.get_google_integration(db=db, user_id=user_id)
    if integ is None:
        errors.append("plan_sessions_skip:no_google_integration")
        return [], errors
    if not has_required_scopes(integ):
        errors.append("plan_sessions_skip:insufficient_scopes")
        return [], errors

    if not isinstance(user_timezone, str) or not user_timezone.strip():
        user_timezone = "UTC"
    try:
        tz = ZoneInfo(user_timezone)
    except Exception:  # noqa: BLE001
        user_timezone = "UTC"
        tz = ZoneInfo("UTC")

    safe_windows: list[dict[str, str]] = [
        w
        for w in (preferred_windows or [])
        if isinstance(w, dict)
        and isinstance(w.get("start"), str)
        and isinstance(w.get("end"), str)
    ]

    now = now_utc or datetime.now(timezone.utc)
    today_local = now.astimezone(tz).date()
    results: list[dict[str, Any]] = []

    for day_index, day_item in enumerate(schedule_items):
        if not isinstance(day_item, dict):
            errors.append(f"plan_sessions_skip:day={day_index}:invalid_schedule_item")
            continue
        tasks_raw = day_item.get("tasks")
        tasks: list[str] = (
            [str(t) for t in tasks_raw if isinstance(t, str)]
            if isinstance(tasks_raw, list)
            else []
        )

        target_date = today_local + timedelta(days=day_index)
        day_start_local = datetime.combine(target_date, time(0, 0), tzinfo=tz)
        day_end_local = day_start_local + timedelta(days=1)
        base_start = max(now, day_start_local.astimezone(timezone.utc))
        if day_end_local.astimezone(timezone.utc) <= base_start:
            errors.append(f"plan_sessions_skip:day={day_index}:day_already_elapsed")
            continue

        # One freebusy range: primary + GradePilot busy through a small spill
        # horizon so later days can find a slot even if the target calendar day
        # is packed (we still create one event per plan day).
        spill_horizon_end_local = day_start_local + timedelta(days=8)
        busy_end = spill_horizon_end_local.astimezone(timezone.utc)
        try:
            busy_blocks = list_busy_blocks(
                db=db,
                user_id=str(user_id),
                start=base_start,
                end=busy_end,
            )
        except Exception as e:  # noqa: BLE001
            errors.append(
                f"plan_sessions_busy_failed:day={day_index}:{e.__class__.__name__}"
            )
            continue

        slot = None
        for extend_days in range(0, 7):
            probe_end_local = day_start_local + timedelta(days=1 + extend_days)
            probe_end = probe_end_local.astimezone(timezone.utc)
            if probe_end > busy_end:
                probe_end = busy_end
            if probe_end <= base_start:
                continue
            try:
                slot = find_first_available_slot(
                    busy_blocks=busy_blocks,
                    preferred_windows=safe_windows,
                    user_timezone=user_timezone,
                    search_start=base_start,
                    search_end=probe_end,
                    min_lookahead_minutes=(
                        15 if day_index == 0 and extend_days == 0 else 0
                    ),
                )
            except Exception as e:  # noqa: BLE001
                errors.append(
                    f"plan_sessions_slot_failed:day={day_index}:{e.__class__.__name__}"
                )
                slot = None
                break
            if slot is not None:
                break

        if slot is None:
            errors.append(f"plan_sessions_skip:day={day_index}:no_slot_found")
            continue

        day_label = str(day_item.get("day") or "").strip() or f"Day {day_index + 1}"
        desc_lines = [
            f"Study plan: {day_label}",
            "",
            "Tasks:",
            *(f"- {t}" for t in tasks),
        ]
        description = "\n".join(desc_lines).strip()

        try:
            event = upsert_plan_day_event(
                db=db,
                user_id=str(user_id),
                class_id=class_id,
                plan_id=plan_id,
                day_index=day_index,
                title=f"{class_title} — {day_label}",
                start=slot.start,
                end=slot.end,
                description=description,
            )
        except Exception as e:  # noqa: BLE001
            errors.append(
                f"plan_sessions_create_failed:day={day_index}:{e.__class__.__name__}"
            )
            continue

        results.append(
            {
                "day_index": day_index,
                "day_label": day_label,
                "tasks": tasks,
                "start": slot.start.isoformat(),
                "end": slot.end.isoformat(),
                "in_preferred_window": slot.in_preferred_window,
                "calendar_event_link": event.get("html_link", ""),
                "calendar_event_id": event.get("event_id", ""),
            }
        )

    return results, errors
