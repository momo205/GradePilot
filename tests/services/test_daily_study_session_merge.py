from __future__ import annotations

from app.services.google_calendar import _merge_daily_study_description


def test_merge_description_creates_new_when_empty() -> None:
    out = _merge_daily_study_description(
        existing_description="",
        day_label="Day 1",
        date_local_iso="2026-05-11",
        class_title="CS101",
        tasks=["Read notes", "Practice problems"],
    )
    assert "Study session — Day 1" in out
    assert "Date: 2026-05-11" in out
    assert "### CS101" in out
    assert "- Read notes" in out


def test_merge_description_appends_second_class() -> None:
    first = _merge_daily_study_description(
        existing_description="",
        day_label="Day 1",
        date_local_iso="2026-05-11",
        class_title="CS101",
        tasks=["Read notes"],
    )
    second = _merge_daily_study_description(
        existing_description=first,
        day_label="Day 1",
        date_local_iso="2026-05-11",
        class_title="MATH308",
        tasks=["Problem set"],
    )
    assert "### CS101" in second
    assert "### MATH308" in second
    assert "- Problem set" in second


def test_merge_description_replaces_class_section() -> None:
    base = _merge_daily_study_description(
        existing_description="",
        day_label="Day 1",
        date_local_iso="2026-05-11",
        class_title="CS101",
        tasks=["Old task"],
    )
    updated = _merge_daily_study_description(
        existing_description=base,
        day_label="Day 1",
        date_local_iso="2026-05-11",
        class_title="CS101",
        tasks=["New task"],
    )
    assert "- New task" in updated
    assert "- Old task" not in updated
