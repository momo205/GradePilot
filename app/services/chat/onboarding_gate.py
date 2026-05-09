from __future__ import annotations

import json
from typing import Any

WELCOME_MESSAGE = """Welcome to GradePilot.

Let’s set up one class. Start by sending the class name, e.g.:
`{"class_title":"CS 301 — Algorithms"}`"""


def initial_state() -> dict[str, Any]:
    # The frontend onboarding chat is a single-class wizard with numeric phases 1-5.
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

    # Accept both start/end and semester_start/semester_end
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
    if phase < 1 or phase > 5:
        phase = 1
    st["phase"] = phase

    # Accept semester timeline any time; store on state for later steps.
    fields = _parse_semester_fields(msg)
    timezone_val = fields.get("timezone")
    sem_start = fields.get("semester_start")
    sem_end = fields.get("semester_end")
    if timezone_val and sem_start and sem_end:
        st["timezone"] = timezone_val
        st["semester_start"] = sem_start
        st["semester_end"] = sem_end

    # Phase 1 — collect class title
    if phase == 1:
        title = _get_str(msg_json, "class_title")
        if title:
            tool_actions.append({"type": "create_class", "payload": {"title": title[:200]}})
            st["phase"] = 2
            return (
                f'Got it. **{title[:200]}**.\n\n'
                "Next: send your semester timeline as either:\n"
                "- `timezone=America/New_York; start=YYYY-MM-DD; end=YYYY-MM-DD` or\n"
                '- JSON: `{"timezone":"...","semester_start":"...","semester_end":"..."}`',
                st,
                tool_actions,
            )
        return (
            "Send your class name as JSON, e.g.\n"
            '`{"class_title":"CS 301 — Algorithms"}`',
            st,
            tool_actions,
        )

    # Phase 2 — semester timeline
    if phase == 2:
        if timezone_val and sem_start and sem_end:
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
            st["phase"] = 3
            return (
                "Timeline saved.\n\n"
                "Now upload your **syllabus PDF** to import deadlines, or add deadlines manually.",
                st,
                tool_actions,
            )
        return (
            "Send your semester timeline:\n"
            "`timezone=America/New_York; start=YYYY-MM-DD; end=YYYY-MM-DD`\n"
            "or JSON: `{\"timezone\":\"...\",\"semester_start\":\"...\",\"semester_end\":\"...\"}`",
            st,
            tool_actions,
        )

    # Phase 3 — deadlines (syllabus import or manual deadlines)
    if phase == 3:
        # UI sends "done" when finished adding/importing deadlines.
        if msg.lower() == "done" or msg_json.get("done") is True:
            st["phase"] = 4
            return (
                "Great. Optionally upload readings/notes/slides for Q&A.\n\n"
                "When finished, click **Done → Generate plan**.",
                st,
                tool_actions,
            )

        if msg_json.get("deadlines_imported") is True:
            return (
                "Deadlines imported.\n\n"
                "Add more deadlines if needed, then click **Done with deadlines**.",
                st,
                tool_actions,
            )

        deadline = msg_json.get("deadline")
        if isinstance(deadline, dict):
            title = _get_str(deadline, "title")
            due = _get_str(deadline, "due")
            if title and due:
                tool_actions.append(
                    {"type": "create_deadline", "payload": {"title": title, "due_text": due}}
                )
                return ("Added. Add another, or click **Done with deadlines**.", st, tool_actions)

        return (
            "Upload your **syllabus PDF** to import deadlines, or add one manually.\n"
            "When finished, click **Done with deadlines**.",
            st,
            tool_actions,
        )

    # Phase 4 — optional materials, then generate plan
    if phase == 4:
        if msg.lower() == "done" or msg_json.get("done") is True:
            tool_actions.append({"type": "generate_semester_plan", "payload": {}})
            st["phase"] = 5
            return ("Generating your study plan…", st, tool_actions)
        return (
            "Optionally upload PDFs / paste text to index for Q&A.\n"
            "When finished, click **Done → Generate plan**.",
            st,
            tool_actions,
        )

    # Phase 5 — generating / complete (router will redirect)
    st["phase"] = 5
    return ("Generating your study plan…", st, tool_actions)
