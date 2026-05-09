from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.services.scheduling.slot_finder import (
    CandidateSlot,
    find_first_available_slot,
)

NY = ZoneInfo("America/New_York")
UTC = timezone.utc
EVENING = {"start": "19:00", "end": "23:00"}
MORNING = {"start": "07:00", "end": "10:00"}


def test_finds_slot_in_first_preferred_window() -> None:
    # Tue 14:00 NY local. Earliest allowed start is 15:00 NY (lookahead).
    # Preferred evening window 19:00-23:00 has no busy blocks; we expect 19:00.
    search_start = datetime(2026, 9, 15, 14, 0, tzinfo=NY)
    search_end = search_start + timedelta(days=2)
    slot = find_first_available_slot(
        busy_blocks=[],
        preferred_windows=[EVENING],
        user_timezone="America/New_York",
        search_start=search_start,
        search_end=search_end,
    )
    assert slot is not None
    assert slot.in_preferred_window is True
    assert slot.start == datetime(2026, 9, 15, 19, 0, tzinfo=NY)
    assert slot.end == datetime(2026, 9, 15, 20, 0, tzinfo=NY)


def test_skips_busy_blocks_within_preferred_window() -> None:
    # Preferred evening 19-23. Busy 19:00-21:00. Expect 21:00 start.
    search_start = datetime(2026, 9, 15, 14, 0, tzinfo=NY)
    search_end = search_start + timedelta(days=2)
    busy = [
        (
            datetime(2026, 9, 15, 19, 0, tzinfo=NY),
            datetime(2026, 9, 15, 21, 0, tzinfo=NY),
        )
    ]
    slot = find_first_available_slot(
        busy_blocks=busy,
        preferred_windows=[EVENING],
        user_timezone="America/New_York",
        search_start=search_start,
        search_end=search_end,
    )
    assert slot is not None
    assert slot.in_preferred_window is True
    assert slot.start == datetime(2026, 9, 15, 21, 0, tzinfo=NY)


def test_falls_back_to_non_preferred_when_preferred_fully_booked() -> None:
    # Preferred evening fully booked across the whole search window;
    # expect a non-preferred slot.
    search_start = datetime(2026, 9, 15, 14, 0, tzinfo=NY)
    search_end = datetime(2026, 9, 16, 18, 0, tzinfo=NY)
    busy = [
        # Full evening window day 1 (19:00-23:00).
        (
            datetime(2026, 9, 15, 19, 0, tzinfo=NY),
            datetime(2026, 9, 15, 23, 0, tzinfo=NY),
        ),
        # Full evening window day 2 — but search ends before this matters.
        (
            datetime(2026, 9, 16, 19, 0, tzinfo=NY),
            datetime(2026, 9, 16, 23, 0, tzinfo=NY),
        ),
    ]
    slot = find_first_available_slot(
        busy_blocks=busy,
        preferred_windows=[EVENING],
        user_timezone="America/New_York",
        search_start=search_start,
        search_end=search_end,
    )
    assert slot is not None
    assert slot.in_preferred_window is False
    # Lookahead is 60 min, so earliest is 15:00; first 15-min boundary >= 15:00
    # that isn't busy is 15:00 itself.
    assert slot.start == datetime(2026, 9, 15, 15, 0, tzinfo=NY)


def test_returns_none_when_search_window_is_too_short_for_lookahead() -> None:
    search_start = datetime(2026, 9, 15, 14, 0, tzinfo=NY)
    search_end = search_start + timedelta(minutes=30)  # < 60 lookahead
    slot = find_first_available_slot(
        busy_blocks=[],
        preferred_windows=[EVENING],
        user_timezone="America/New_York",
        search_start=search_start,
        search_end=search_end,
    )
    assert slot is None


def test_returns_none_when_everything_is_busy() -> None:
    search_start = datetime(2026, 9, 15, 14, 0, tzinfo=NY)
    search_end = search_start + timedelta(hours=4)
    busy = [(search_start, search_end)]
    slot = find_first_available_slot(
        busy_blocks=busy,
        preferred_windows=[],
        user_timezone="America/New_York",
        search_start=search_start,
        search_end=search_end,
    )
    assert slot is None


def test_evening_window_means_user_local_not_utc() -> None:
    # User is in Tokyo (UTC+9). Preferred 19:00-22:00 Tokyo == 10:00-13:00 UTC.
    # Search starts at 03:00 UTC (12:00 Tokyo). Lookahead 60 min -> earliest
    # 04:00 UTC == 13:00 Tokyo. The first preferred slot must be 19:00 Tokyo
    # the same day = 10:00 UTC the next day. Wait, 13:00 Tokyo Sep 15 -> next
    # 19:00 Tokyo is Sep 15 19:00 == Sep 15 10:00 UTC. 10 UTC is *before* 04
    # UTC the next day but *after* 04 UTC same day. Walk through:
    tokyo = ZoneInfo("Asia/Tokyo")
    search_start = datetime(2026, 9, 15, 3, 0, tzinfo=UTC)  # 12:00 Tokyo
    search_end = search_start + timedelta(days=2)
    slot = find_first_available_slot(
        busy_blocks=[],
        preferred_windows=[{"start": "19:00", "end": "22:00"}],
        user_timezone="Asia/Tokyo",
        search_start=search_start,
        search_end=search_end,
    )
    assert slot is not None
    assert slot.in_preferred_window is True
    # 19:00 Tokyo on Sep 15.
    assert slot.start.astimezone(tokyo) == datetime(2026, 9, 15, 19, 0, tzinfo=tokyo)


def test_respects_min_lookahead_minutes() -> None:
    # No busy blocks, evening window. Set lookahead so the first 19:00 slot
    # is within the lookahead window and must be skipped to the next 15 min.
    search_start = datetime(2026, 9, 15, 18, 30, tzinfo=NY)
    search_end = search_start + timedelta(days=1)
    # 60-min lookahead -> earliest allowed = 19:30. First slot in window is 19:30.
    slot = find_first_available_slot(
        busy_blocks=[],
        preferred_windows=[EVENING],
        user_timezone="America/New_York",
        search_start=search_start,
        search_end=search_end,
        min_lookahead_minutes=60,
    )
    assert slot is not None
    assert slot.start == datetime(2026, 9, 15, 19, 30, tzinfo=NY)


def test_15_minute_granularity() -> None:
    # search_start at :07. First valid local boundary >= :07 + 60 lookahead
    # (= :07 + 1h = next hour :07) -> rounded up to next :15 boundary.
    search_start = datetime(2026, 9, 15, 14, 7, tzinfo=NY)
    search_end = search_start + timedelta(days=1)
    slot = find_first_available_slot(
        busy_blocks=[],
        preferred_windows=[],  # force fallback so we exercise the grid directly
        user_timezone="America/New_York",
        search_start=search_start,
        search_end=search_end,
    )
    assert slot is not None
    # 14:07 + 60 = 15:07 -> round up to 15:15.
    assert slot.start == datetime(2026, 9, 15, 15, 15, tzinfo=NY)
    assert slot.start.minute % 15 == 0


def test_slot_must_fully_fit_inside_preferred_window() -> None:
    # Preferred 19:00-19:30 (only 30 min) can't hold a 60-min slot.
    # Should fall back to non-preferred.
    search_start = datetime(2026, 9, 15, 14, 0, tzinfo=NY)
    search_end = search_start + timedelta(hours=12)
    slot = find_first_available_slot(
        busy_blocks=[],
        preferred_windows=[{"start": "19:00", "end": "19:30"}],
        user_timezone="America/New_York",
        search_start=search_start,
        search_end=search_end,
    )
    assert slot is not None
    assert slot.in_preferred_window is False
    assert slot.start == datetime(2026, 9, 15, 15, 0, tzinfo=NY)


def test_naive_datetimes_raise() -> None:
    with pytest.raises(ValueError):
        find_first_available_slot(
            busy_blocks=[],
            preferred_windows=[],
            user_timezone="UTC",
            search_start=datetime(2026, 9, 15, 14, 0),
            search_end=datetime(2026, 9, 16, 14, 0, tzinfo=UTC),
        )


def test_invalid_duration_raises() -> None:
    with pytest.raises(ValueError):
        find_first_available_slot(
            busy_blocks=[],
            preferred_windows=[],
            user_timezone="UTC",
            search_start=datetime(2026, 9, 15, tzinfo=UTC),
            search_end=datetime(2026, 9, 16, tzinfo=UTC),
            duration_minutes=37,
        )


def test_busy_block_only_partially_overlaps_skips_just_those_15min_slots() -> None:
    # Busy 19:30-20:00. 60-min slot at 19:00 overlaps (19:00-20:00 vs 19:30-20:00).
    # 19:15 also overlaps. 19:30 also overlaps. 20:00-21:00 is clear.
    search_start = datetime(2026, 9, 15, 14, 0, tzinfo=NY)
    search_end = search_start + timedelta(days=1)
    busy = [
        (
            datetime(2026, 9, 15, 19, 30, tzinfo=NY),
            datetime(2026, 9, 15, 20, 0, tzinfo=NY),
        )
    ]
    slot = find_first_available_slot(
        busy_blocks=busy,
        preferred_windows=[EVENING],
        user_timezone="America/New_York",
        search_start=search_start,
        search_end=search_end,
    )
    assert slot is not None
    assert slot.in_preferred_window is True
    assert slot.start == datetime(2026, 9, 15, 20, 0, tzinfo=NY)


def test_morning_window_picked_when_earlier_than_evening() -> None:
    # Search starts night before; first preferred window the next day is morning.
    search_start = datetime(2026, 9, 14, 23, 0, tzinfo=NY)
    search_end = search_start + timedelta(days=2)
    slot = find_first_available_slot(
        busy_blocks=[],
        preferred_windows=[MORNING, EVENING],
        user_timezone="America/New_York",
        search_start=search_start,
        search_end=search_end,
    )
    assert slot is not None
    assert slot == CandidateSlot(
        start=datetime(2026, 9, 15, 7, 0, tzinfo=NY),
        end=datetime(2026, 9, 15, 8, 0, tzinfo=NY),
        in_preferred_window=True,
    )


def test_dst_spring_forward_does_not_return_invalid_local_time() -> None:
    # 2026-03-08 02:00 EST -> 03:00 EDT in NY. Search around the gap.
    # Preferred 02:00-04:00 doesn't exist in local clock terms during the gap;
    # the slot must still land at a real local time on the EDT side.
    search_start = datetime(2026, 3, 7, 22, 0, tzinfo=NY)  # Sat night
    search_end = search_start + timedelta(hours=12)
    slot = find_first_available_slot(
        busy_blocks=[],
        preferred_windows=[{"start": "03:00", "end": "06:00"}],
        user_timezone="America/New_York",
        search_start=search_start,
        search_end=search_end,
    )
    assert slot is not None
    assert slot.in_preferred_window is True
    # 03:00 EDT on Sunday after spring-forward = 07:00 UTC.
    assert slot.start.astimezone(UTC) == datetime(2026, 3, 8, 7, 0, tzinfo=UTC)
