from __future__ import annotations

import re
from datetime import datetime, time
from zoneinfo import ZoneInfo

_RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_user_due_to_datetime(*, due: str, timezone: str | None) -> datetime | None:
    """
    Best-effort parsing for user-entered due strings.

    Supported:
    - ISO 8601 datetime (e.g. "2026-10-05T23:59:00-04:00" or "...Z")
    - Date-only "YYYY-MM-DD" -> interpreted as 23:59:00 in the provided timezone

    Returns None if parsing fails.
    """
    raw = (due or "").strip()
    if raw == "":
        return None

    # Allow Z suffix
    iso = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(iso)
        return dt
    except Exception:
        pass

    if not _RE_DATE.match(raw):
        return None

    # Date-only: interpret as end-of-day in user's timezone (or UTC if unknown).
    tz_name = (timezone or "").strip() or "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")
    try:
        day = datetime.fromisoformat(raw).date()
    except Exception:
        return None
    return datetime.combine(day, time(23, 59, 0), tzinfo=tz)

