from __future__ import annotations

from typing import Any, Literal, Optional, TypedDict


class ReplannerState(TypedDict):
    # Inputs
    user_id: str
    class_id: str
    trigger: Literal[
        "onboarding",
        "deadline_imported",
        "deadline_added",
        "notes_added",
        "progress_updated",
        "manual_replan",
    ]
    dry_run: bool
    force_replan: bool
    sync_calendar_override: Optional[bool]  # None = use user_settings
    # When True, ``schedule_study_session`` runs even if the user's
    # ``auto_schedule_sessions`` flag is False and even if the trigger is not
    # ``notes_added`` (e.g. the user clicked a manual "Schedule now" button).
    force_schedule_session: bool

    # Loaded context (filled by load_context node)
    class_data: Optional[dict[str, Any]]
    deadlines: Optional[list[dict[str, Any]]]
    latest_plan: Optional[dict[str, Any]]
    notes: Optional[list[dict[str, Any]]]
    user_settings: Optional[dict[str, Any]]
    has_google_integration: bool

    # Decision artifacts
    should_replan: Optional[bool]
    replan_reason: Optional[str]
    change_signals: Optional[dict[str, Any]]  # what materially changed

    # Outputs
    new_plan: Optional[dict[str, Any]]
    new_plan_id: Optional[str]
    calendar_sync_result: Optional[dict[str, Any]]
    completed_tasks_carried: Optional[list[Any]]
    # Set by schedule_study_session on notes_added when auto-scheduling is on.
    # Shape: {"start": iso, "end": iso, "in_preferred_window": bool,
    #         "calendar_event_link": str} or None when nothing was scheduled
    # (skipped, no slot found, or failed -- failures also push to errors).
    scheduled_session: Optional[dict[str, Any]]
    # Set by schedule_plan_sessions: one entry per day in the freshly-generated
    # plan, in plan order. Each entry has the same shape as scheduled_session
    # plus "day_index" (0-based) and "tasks" (list[str] copied from plan_json).
    # Empty list when no plan was just generated, when auto-scheduling is off,
    # or when no slots were found for any day.
    scheduled_plan_sessions: Optional[list[dict[str, Any]]]

    # Status
    errors: list[str]
