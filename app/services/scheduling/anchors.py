"""Pure anchor calculation for the focused study session scheduler.

Given a class (with optional `meeting_pattern`), its known deadlines, and a
"now" instant, compute the next pedagogically meaningful moment that a study
session should be scheduled to land *before*.

This module performs no I/O and no LLM calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

AnchorKind = Literal["next_lecture", "next_deadline", "fallback"]


@dataclass(frozen=True)
class Anchor:
    at: datetime
    kind: AnchorKind
    reference_id: str | None


def _resolve_tz(class_data: dict[str, Any]) -> ZoneInfo:
    tz_name = class_data.get("timezone")
    if isinstance(tz_name, str) and tz_name.strip():
        return ZoneInfo(tz_name)
    return ZoneInfo("UTC")


def _parse_hhmm(value: object) -> tuple[int, int] | None:
    if not isinstance(value, str) or len(value) != 5 or value[2] != ":":
        return None
    try:
        hh = int(value[:2])
        mm = int(value[3:])
    except ValueError:
        return None
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    return hh, mm


def _parse_date(value: object) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None


def _parse_due_at(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else None
    if isinstance(value, str) and value.strip():
        s = value.strip()
        # Accept trailing "Z" as UTC (datetime.fromisoformat in <3.11 didn't).
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            return None
        return dt if dt.tzinfo is not None else None
    return None


def _next_meeting_in_tz(
    *,
    pattern: dict[str, Any],
    from_local: datetime,
) -> datetime | None:
    """Compute the next pattern occurrence at-or-after ``from_local``.

    ``from_local`` must already be in the class timezone. The returned datetime
    carries the same ``tzinfo``. Returns None if the pattern is malformed or
    has no usable weekdays.
    """
    weekdays_raw = pattern.get("weekdays")
    if not isinstance(weekdays_raw, list) or not weekdays_raw:
        return None
    weekdays: list[int] = []
    for w in weekdays_raw:
        if isinstance(w, bool):
            # bool is a subclass of int; reject explicitly.
            return None
        if not isinstance(w, int) or not 0 <= w <= 6:
            continue
        weekdays.append(w)
    if not weekdays:
        return None

    parsed = _parse_hhmm(pattern.get("start_time"))
    if parsed is None:
        return None
    hh, mm = parsed

    candidates: list[datetime] = []
    for weekday in weekdays:
        days_ahead = (weekday - from_local.weekday()) % 7
        candidate_date = from_local.date() + timedelta(days=days_ahead)
        # Build a wall-clock datetime in the class timezone. Constructing with
        # `tzinfo=ZoneInfo(...)` lets ZoneInfo apply the right UTC offset for
        # that local date, which is how we get DST correctness.
        candidate = datetime.combine(
            candidate_date, time(hh, mm), tzinfo=from_local.tzinfo
        )
        if candidate <= from_local:
            candidate = candidate + timedelta(days=7)
        candidates.append(candidate)
    return min(candidates)


def _semester_end_eod(class_data: dict[str, Any], tz: ZoneInfo) -> datetime | None:
    end_date = _parse_date(class_data.get("semester_end"))
    if end_date is None:
        return None
    # End-of-day on the last day, in class timezone.
    return datetime.combine(end_date, time(23, 59, 59), tzinfo=tz)


def compute_next_anchor(
    *,
    class_data: dict[str, Any],
    deadlines: list[dict[str, Any]],
    from_dt: datetime,
) -> Anchor:
    """Return the earliest of (next lecture, next deadline, fallback).

    All comparisons happen in absolute time; the returned ``Anchor.at`` is
    converted to the class timezone for caller convenience.

    ``from_dt`` MUST be timezone-aware. ``deadlines`` entries with naive or
    missing ``due_at`` values are ignored.

    Fallback is ``from_dt + 7 days``, capped at ``semester_end`` (end-of-day in
    class timezone) when that field is present. ``next_lecture`` is similarly
    suppressed if it would land after ``semester_end``.
    """
    if from_dt.tzinfo is None:
        raise ValueError("from_dt must be timezone-aware")

    tz = _resolve_tz(class_data)
    from_local = from_dt.astimezone(tz)
    semester_cap = _semester_end_eod(class_data, tz)

    candidates: list[Anchor] = []

    pattern = class_data.get("meeting_pattern")
    if isinstance(pattern, dict):
        next_lecture = _next_meeting_in_tz(pattern=pattern, from_local=from_local)
        if next_lecture is not None and (
            semester_cap is None or next_lecture <= semester_cap
        ):
            candidates.append(
                Anchor(at=next_lecture, kind="next_lecture", reference_id=None)
            )

    next_deadline_at: datetime | None = None
    next_deadline_id: str | None = None
    for d in deadlines:
        if not isinstance(d, dict):
            continue
        due_at = _parse_due_at(d.get("due_at"))
        if due_at is None or due_at <= from_dt:
            continue
        if next_deadline_at is None or due_at < next_deadline_at:
            next_deadline_at = due_at
            did = d.get("id")
            next_deadline_id = str(did) if did is not None else None
    if next_deadline_at is not None:
        candidates.append(
            Anchor(
                at=next_deadline_at.astimezone(tz),
                kind="next_deadline",
                reference_id=next_deadline_id,
            )
        )

    fallback_at = from_dt + timedelta(days=7)
    if semester_cap is not None and fallback_at > semester_cap:
        fallback_at = semester_cap
    candidates.append(
        Anchor(at=fallback_at.astimezone(tz), kind="fallback", reference_id=None)
    )

    return min(candidates, key=lambda a: a.at)
