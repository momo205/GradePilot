"""Greedy first-fit search for a study session slot.

Pure function: no I/O, no LLM. Inputs are an opaque list of busy intervals
(typically pulled from `list_busy_blocks`) and a list of daily preferred
windows in the user's local time.

The search proceeds in two passes:

1. Walk forward from ``search_start`` in 15-minute increments aligned to the
   user-local clock. For each candidate, require:
     * no overlap with any busy block
     * candidate fully contained in at least one preferred window
     * candidate start >= ``search_start + min_lookahead_minutes``
     * candidate end <= ``search_end``
   Return the first hit.

2. If pass 1 finds nothing, repeat without the preferred-window constraint
   and return the first hit (with ``in_preferred_window=False``).

If both passes fail, return ``None``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class CandidateSlot:
    start: datetime
    end: datetime
    in_preferred_window: bool


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


def _round_up_to_next_15(dt: datetime) -> datetime:
    """Round ``dt`` up to the next 15-minute wall-clock boundary in its tz.

    If ``dt`` is already exactly on a 15-min boundary (and has no sub-minute
    component) it is returned unchanged.
    """
    minute_offset = (15 - dt.minute % 15) % 15
    if minute_offset == 0 and dt.second == 0 and dt.microsecond == 0:
        return dt
    if minute_offset == 0:
        minute_offset = 15
    return dt.replace(second=0, microsecond=0) + timedelta(minutes=minute_offset)


def _slot_overlaps_busy(
    slot_start: datetime,
    slot_end: datetime,
    busy_blocks: list[tuple[datetime, datetime]],
) -> bool:
    for bs, be in busy_blocks:
        if slot_start < be and bs < slot_end:
            return True
    return False


def _slot_in_preferred_window(
    slot_local_start: datetime,
    slot_local_end: datetime,
    parsed_windows: list[tuple[tuple[int, int], tuple[int, int]]],
    tz: ZoneInfo,
) -> bool:
    if not parsed_windows:
        return False
    # A slot that crosses midnight in user-local time can't fit in any single
    # daily window (start < end is enforced upstream).
    if slot_local_start.date() != slot_local_end.date():
        # Allow exact-midnight ends (00:00 of next day) only if a window
        # ends at 23:59 — but our HH:MM grid maxes at 23:59 so any cross
        # is genuinely outside every window. Reject.
        return False
    day = slot_local_start.date()
    for (sh, sm), (eh, em) in parsed_windows:
        win_start = datetime.combine(day, time(sh, sm), tzinfo=tz)
        win_end = datetime.combine(day, time(eh, em), tzinfo=tz)
        if slot_local_start >= win_start and slot_local_end <= win_end:
            return True
    return False


def _validate_inputs(
    *,
    user_timezone: str,
    search_start: datetime,
    search_end: datetime,
    duration_minutes: int,
    min_lookahead_minutes: int,
) -> ZoneInfo:
    if search_start.tzinfo is None or search_end.tzinfo is None:
        raise ValueError("search_start and search_end must be timezone-aware")
    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be positive")
    if duration_minutes % 15 != 0:
        # Not strictly required by the spec, but mixing a 15-min cursor with a
        # non-multiple duration would silently drop perfectly valid slots.
        raise ValueError("duration_minutes must be a multiple of 15")
    if min_lookahead_minutes < 0:
        raise ValueError("min_lookahead_minutes must be >= 0")
    return ZoneInfo(user_timezone)


def _parse_windows(
    preferred_windows: list[dict[str, Any]],
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    parsed: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for w in preferred_windows:
        if not isinstance(w, dict):
            continue
        start = _parse_hhmm(w.get("start"))
        end = _parse_hhmm(w.get("end"))
        if start is None or end is None:
            continue
        if start >= end:
            continue
        parsed.append((start, end))
    return parsed


def find_first_available_slot(
    *,
    busy_blocks: list[tuple[datetime, datetime]],
    preferred_windows: list[dict[str, Any]],
    user_timezone: str,
    search_start: datetime,
    search_end: datetime,
    duration_minutes: int = 60,
    min_lookahead_minutes: int = 60,
) -> CandidateSlot | None:
    tz = _validate_inputs(
        user_timezone=user_timezone,
        search_start=search_start,
        search_end=search_end,
        duration_minutes=duration_minutes,
        min_lookahead_minutes=min_lookahead_minutes,
    )

    earliest_allowed = search_start + timedelta(minutes=min_lookahead_minutes)
    if earliest_allowed >= search_end:
        return None

    cursor_local = _round_up_to_next_15(earliest_allowed.astimezone(tz))
    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=15)
    parsed_windows = _parse_windows(preferred_windows)

    def _scan(*, require_preferred: bool) -> CandidateSlot | None:
        cursor = cursor_local
        while True:
            slot_end_local = cursor + duration
            if slot_end_local > search_end:
                return None
            if cursor >= earliest_allowed and not _slot_overlaps_busy(
                cursor, slot_end_local, busy_blocks
            ):
                in_preferred = _slot_in_preferred_window(
                    cursor, slot_end_local, parsed_windows, tz
                )
                if require_preferred:
                    if in_preferred:
                        return CandidateSlot(
                            start=cursor,
                            end=slot_end_local,
                            in_preferred_window=True,
                        )
                else:
                    return CandidateSlot(
                        start=cursor,
                        end=slot_end_local,
                        in_preferred_window=in_preferred,
                    )
            cursor = cursor + step

    found = _scan(require_preferred=True)
    if found is not None:
        return found
    return _scan(require_preferred=False)
