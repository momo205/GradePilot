from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OnboardingResult:
    assistant_message: str
    state: dict[str, Any]
    tool_actions: list[dict[str, Any]]


WELCOME_MESSAGE = """Welcome to GradePilot.

To get started, send:
- your **classes** (comma-separated), and
- your **semester timeline**.

Examples:
- Classes: `CS101, Calculus II`
- Timeline: `timezone=America/New_York; start=2026-09-01; end=2026-12-15`

Then upload your **syllabus** (PDF) for each class to import deadlines."""


def welcome_message() -> str:
    return WELCOME_MESSAGE


def initial_state() -> dict[str, Any]:
    return {"phase": "need_materials"}


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


def run_onboarding_step(
    *,
    state: dict[str, Any],
    user_message: str,
) -> OnboardingResult:
    """Deterministic onboarding used by tests + UI.

    Phases are strings to keep state explicit across versions.
    """

    st = dict(state or {})
    tool_actions: list[dict[str, Any]] = []

    msg = (user_message or "").strip()
    msg_json = _parse_json_message(msg) or {}

    phase = st.get("phase")
    if not isinstance(phase, str) or not phase:
        phase = "need_materials"
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

    # Parse class list in comma-separated form or JSON.
    titles: list[str] = []
    raw_titles = msg_json.get("classes")
    if isinstance(raw_titles, list):
        for t in raw_titles:
            if isinstance(t, str) and t.strip():
                titles.append(t.strip()[:200])
    if not titles and "," in msg:
        for part in msg.split(","):
            t = part.strip()
            if t:
                titles.append(t[:200])

    # --- need_materials: ask for classes + timeline; accept either order ---
    if phase == "need_materials":
        if titles:
            tool_actions.append(
                {"type": "create_classes", "payload": {"titles": titles}}
            )
            st["phase"] = "need_syllabi"
            return OnboardingResult(
                assistant_message=(
                    "Got it. Next, upload your **syllabus** (PDF) for each class to import deadlines.\n\n"
                    "If you haven’t yet, also send your semester timeline:\n"
                    "`timezone=America/New_York; start=YYYY-MM-DD; end=YYYY-MM-DD`"
                ),
                state=st,
                tool_actions=tool_actions,
            )

        if timezone_val and sem_start and sem_end:
            st["phase"] = "need_classes"
            return OnboardingResult(
                assistant_message=(
                    "Great — semester timeline saved.\n\n"
                    "Now send your classes as a comma-separated list (e.g. `CS101, Calculus II`)."
                ),
                state=st,
                tool_actions=tool_actions,
            )

        return OnboardingResult(
            assistant_message=(
                "To get started, tell me your classes (comma-separated) and your semester timeline.\n\n"
                "Classes example: `CS101, Calculus II`\n"
                "Timeline example: `timezone=America/New_York; start=2026-09-01; end=2026-12-15`\n\n"
                "Then upload your syllabus PDFs to import deadlines."
            ),
            state=st,
            tool_actions=tool_actions,
        )

    # --- need_classes: after timeline, collect classes ---
    if phase == "need_classes":
        if titles:
            tool_actions.append(
                {"type": "create_classes", "payload": {"titles": titles}}
            )
            st["phase"] = "need_syllabi"
            return OnboardingResult(
                assistant_message=(
                    "Classes created. Next, upload your **syllabus** (PDF) for each class to import deadlines."
                ),
                state=st,
                tool_actions=tool_actions,
            )
        return OnboardingResult(
            assistant_message=(
                "Send your classes as a comma-separated list (e.g. `CS101, Calculus II`).\n"
                "You can also include your timeline: `timezone=...; start=...; end=...`."
            ),
            state=st,
            tool_actions=tool_actions,
        )

    # --- need_syllabi: placeholder for UI upload flow (tests only assert phase) ---
    if phase == "need_syllabi":
        return OnboardingResult(
            assistant_message=(
                "Upload your **syllabus** (PDF) for each class to import deadlines.\n"
                "When you’re ready, you can also ask questions or generate a study plan."
            ),
            state=st,
            tool_actions=tool_actions,
        )

    # Unknown phase fallback (keep it stable).
    st["phase"] = "need_materials"
    return OnboardingResult(
        assistant_message=welcome_message(),
        state=st,
        tool_actions=tool_actions,
    )
