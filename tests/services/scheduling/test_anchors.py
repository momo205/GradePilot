from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from app.services.scheduling.anchors import Anchor, compute_next_anchor

NY = ZoneInfo("America/New_York")
UTC = timezone.utc


def _class(
    *,
    tz: str = "America/New_York",
    meeting_pattern: dict[str, Any] | None = None,
    semester_end: str | None = None,
) -> dict[str, Any]:
    return {
        "timezone": tz,
        "meeting_pattern": meeting_pattern,
        "semester_end": semester_end,
    }


def _deadline(*, due_at: datetime | None, did: str = "d-1") -> dict[str, Any]:
    return {"id": did, "due_at": due_at}


def test_lecture_sooner_than_deadline_returns_lecture() -> None:
    # Wed 14:00 NY local; lectures Mon/Wed at 14:00; deadline 10 days out.
    from_dt = datetime(2026, 9, 16, 14, 0, tzinfo=NY)
    clazz = _class(
        meeting_pattern={
            "weekdays": [0, 2],  # Mon, Wed
            "start_time": "14:00",
            "end_time": "15:30",
        }
    )
    deadline_dt = from_dt + timedelta(days=10)
    anchor = compute_next_anchor(
        class_data=clazz,
        deadlines=[_deadline(due_at=deadline_dt)],
        from_dt=from_dt,
    )
    # The 14:00 candidate is "<= from_dt" so we skip to next Mon at 14:00.
    expected = datetime(2026, 9, 21, 14, 0, tzinfo=NY)
    assert anchor == Anchor(at=expected, kind="next_lecture", reference_id=None)


def test_deadline_sooner_than_lecture_returns_deadline() -> None:
    # Lectures Tue at 09:00; deadline tomorrow.
    from_dt = datetime(2026, 9, 14, 12, 0, tzinfo=NY)  # Mon
    clazz = _class(
        meeting_pattern={
            "weekdays": [1],  # Tue only -> next is Tue 09:00 (~21h away)
            "start_time": "09:00",
            "end_time": "10:30",
        }
    )
    deadline_dt = datetime(2026, 9, 15, 8, 0, tzinfo=NY)  # Tue 08:00 (before lecture)
    anchor = compute_next_anchor(
        class_data=clazz,
        deadlines=[_deadline(due_at=deadline_dt, did="dl-x")],
        from_dt=from_dt,
    )
    assert anchor.kind == "next_deadline"
    assert anchor.at == deadline_dt
    assert anchor.reference_id == "dl-x"


def test_no_pattern_no_deadlines_returns_fallback_seven_days() -> None:
    from_dt = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)
    clazz = _class(tz="UTC", meeting_pattern=None, semester_end=None)
    anchor = compute_next_anchor(class_data=clazz, deadlines=[], from_dt=from_dt)
    assert anchor.kind == "fallback"
    assert anchor.reference_id is None
    assert anchor.at == from_dt + timedelta(days=7)


def test_semester_end_caps_fallback() -> None:
    from_dt = datetime(2026, 12, 10, 12, 0, tzinfo=UTC)
    clazz = _class(tz="UTC", meeting_pattern=None, semester_end="2026-12-12")
    anchor = compute_next_anchor(class_data=clazz, deadlines=[], from_dt=from_dt)
    assert anchor.kind == "fallback"
    # End-of-day on 2026-12-12 in UTC.
    assert anchor.at == datetime(2026, 12, 12, 23, 59, 59, tzinfo=UTC)


def test_semester_end_suppresses_post_semester_lecture() -> None:
    # Last semester day is Friday 2026-12-11. Lectures only Sunday.
    # Next lecture computed would be Sunday 2026-12-13 -> after semester end.
    from_dt = datetime(2026, 12, 11, 9, 0, tzinfo=UTC)  # Friday
    clazz = _class(
        tz="UTC",
        meeting_pattern={
            "weekdays": [6],  # Sunday
            "start_time": "10:00",
            "end_time": "11:00",
        },
        semester_end="2026-12-11",
    )
    anchor = compute_next_anchor(class_data=clazz, deadlines=[], from_dt=from_dt)
    # Lecture is suppressed; fallback (capped at semester_end EOD) wins.
    assert anchor.kind == "fallback"
    assert anchor.at == datetime(2026, 12, 11, 23, 59, 59, tzinfo=UTC)


def test_dst_boundary_lecture_keeps_local_wall_clock() -> None:
    # US DST ended on Sunday 2026-11-01 at 02:00 local time.
    # We start on Saturday 2026-10-31 12:00 NY (still EDT, UTC-4).
    # Lecture pattern: Mondays at 09:00 local. Next Monday is 2026-11-02,
    # by which time NY is on EST (UTC-5). The returned anchor must still be
    # 09:00 local -> 14:00 UTC (not 13:00 UTC, which would mean we ignored DST).
    from_dt = datetime(2026, 10, 31, 12, 0, tzinfo=NY)
    clazz = _class(
        meeting_pattern={
            "weekdays": [0],  # Mon
            "start_time": "09:00",
            "end_time": "10:00",
        }
    )
    anchor = compute_next_anchor(class_data=clazz, deadlines=[], from_dt=from_dt)
    assert anchor.kind == "next_lecture"
    assert anchor.at.tzinfo is not None
    # Local wall clock preserved across the DST boundary.
    assert (anchor.at.year, anchor.at.month, anchor.at.day) == (2026, 11, 2)
    assert (anchor.at.hour, anchor.at.minute) == (9, 0)
    # And the absolute UTC offset reflects EST (UTC-5) post-DST.
    assert anchor.at.utcoffset() == timedelta(hours=-5)


def test_naive_from_dt_raises() -> None:
    with pytest.raises(ValueError):
        compute_next_anchor(
            class_data=_class(tz="UTC"),
            deadlines=[],
            from_dt=datetime(2026, 9, 14, 12, 0),
        )


def test_naive_due_at_is_ignored() -> None:
    # Naive datetimes are bugs per project policy; treat as missing rather than
    # silently scheduling against an ambiguous instant.
    from_dt = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)
    clazz = _class(tz="UTC", meeting_pattern=None)
    anchor = compute_next_anchor(
        class_data=clazz,
        deadlines=[_deadline(due_at=datetime(2026, 9, 15, 12, 0))],  # naive
        from_dt=from_dt,
    )
    assert anchor.kind == "fallback"


def test_past_deadline_is_skipped_in_favor_of_next_one() -> None:
    from_dt = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)
    clazz = _class(tz="UTC", meeting_pattern=None)
    past = from_dt - timedelta(days=1)
    upcoming = from_dt + timedelta(days=2)
    anchor = compute_next_anchor(
        class_data=clazz,
        deadlines=[
            _deadline(due_at=past, did="old"),
            _deadline(due_at=upcoming, did="new"),
        ],
        from_dt=from_dt,
    )
    assert anchor.kind == "next_deadline"
    assert anchor.reference_id == "new"
    assert anchor.at == upcoming.astimezone(ZoneInfo("UTC"))
