from __future__ import annotations

import json
import re
from typing import Any
from zoneinfo import ZoneInfo

WELCOME_MESSAGE = """Welcome to GradePilot.

Let’s set up one class. Start by sending the class name, e.g.:
`{"class_title":"CS 301 — Algorithms"}`

Then you’ll upload your **syllabus PDF** once — we’ll pull deadlines, suggest term dates (fall/spring), and index the syllabus for Q&A."""


def initial_state() -> dict[str, Any]:
    # 1 title → 2 syllabus upload → 3 timeline → 4 generating / complete.
    return {"phase": 1}


def _parse_json_message(message: str) -> dict[str, Any] | None:
    m = (message or "").strip()
    if not (m.startswith("{") and m.endswith("}")):
        return None
    try:
        out = json.loads(m)
    except Exception:
        return None
    return out if isinstance(out, dict) else None


def _parse_semester_fields(message: str) -> dict[str, str]:
    msg_json = _parse_json_message(message)
    if msg_json is not None:
        out_json: dict[str, str] = {}
        for k in ("timezone", "semester_start", "semester_end"):
            v = msg_json.get(k)
            if isinstance(v, str) and v.strip():
                out_json[k] = v.strip()
        return out_json

    fields: dict[str, str] = {}
    for part in (message or "").split(";"):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        fields[k.strip().lower()] = v.strip()

    result: dict[str, str] = {}
    if fields.get("timezone"):
        result["timezone"] = fields["timezone"]
    if fields.get("start"):
        result["semester_start"] = fields["start"]
    if fields.get("end"):
        result["semester_end"] = fields["end"]
    if fields.get("semester_start"):
        result["semester_start"] = fields["semester_start"]
    if fields.get("semester_end"):
        result["semester_end"] = fields["semester_end"]
    return result


_RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_valid_timezone(tz: str) -> bool:
    try:
        ZoneInfo(tz)
        return True
    except Exception:
        return False


def _is_valid_date(d: str) -> bool:
    return bool(_RE_DATE.match(d))


def _phase_as_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except Exception:
            return 1
    return 1


def _get_str(d: dict[str, Any], k: str) -> str | None:
    v = d.get(k)
    if isinstance(v, str) and v.strip():
        return v.strip()
    return None


def run_onboarding_gate(
    *,
    state: dict[str, Any],
    user_message: str,
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    """Pure gate: returns (assistant_message, next_state, tool_actions)."""
    st = dict(state or {})
    tool_actions: list[dict[str, Any]] = []

    msg = (user_message or "").strip()
    msg_json = _parse_json_message(msg) or {}

    phase = _phase_as_int(st.get("phase"))
    # Legacy sessions may still have phase 5 from older builds.
    if phase > 4:
        phase = 4
    if phase < 1:
        phase = 1
    st["phase"] = phase

    fields = _parse_semester_fields(msg)
    timezone_val = fields.get("timezone")
    sem_start = fields.get("semester_start")
    sem_end = fields.get("semester_end")

    # Phase 1 — collect class title
    if phase == 1:
        title = _get_str(msg_json, "class_title")
        if title:
            tool_actions.append(
                {"type": "create_class", "payload": {"title": title[:200]}}
            )
            st["phase"] = 2
            return (
                f"Got it. **{title[:200]}**.\n\n"
                "Next: upload your **syllabus PDF** using the button in Phase 2. "
                "We’ll extract deadlines, infer fall/spring when possible, suggest term dates, "
                "and index the syllabus for Q&A (one upload — please wait until it finishes).",
                st,
                tool_actions,
            )
        return (
            "Send your class name as JSON, e.g.\n"
            '`{"class_title":"CS 301 — Algorithms"}`',
            st,
            tool_actions,
        )

    # Phase 2 — waiting for syllabus (upload handled by /onboarding/syllabus API)
    if phase == 2:
        return (
            "Use **Upload syllabus PDF** below. When processing completes, confirm your "
            "semester (fall or spring) and dates in the next step.",
            st,
            tool_actions,
        )

    # Phase 3 — semester timeline; saving immediately generates the study plan.
    if phase == 3:
        if (
            timezone_val
            and sem_start
            and sem_end
            and _is_valid_timezone(timezone_val)
            and _is_valid_date(sem_start)
            and _is_valid_date(sem_end)
        ):
            tool_actions.append(
                {
                    "type": "set_class_timeline",
                    "payload": {
                        "timezone": timezone_val,
                        "semester_start": sem_start,
                        "semester_end": sem_end,
                    },
                }
            )
            tool_actions.append({"type": "generate_semester_plan", "payload": {}})
            st["timezone"] = timezone_val
            st["semester_start"] = sem_start
            st["semester_end"] = sem_end
            st["phase"] = 4
            return (
                "Timeline saved. Generating your study plan…\n\n"
                "You can upload readings or notes later from your class page.",
                st,
                tool_actions,
            )
        return (
            "Choose **Fall** or **Spring** (or keep dates extracted from your syllabus), "
            "confirm timezone and start/end dates, then click **Save & generate plan**.\n\n"
            "You can also send JSON:\n"
            '`{"timezone":"America/New_York","semester_start":"2026-08-01","semester_end":"2026-12-20"}`',
            st,
            tool_actions,
        )

    # Phase 4 — generating / complete (router will redirect)
    st["phase"] = 4
    return ("Generating your study plan…", st, tool_actions)
