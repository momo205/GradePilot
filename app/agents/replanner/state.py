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

    # Status
    errors: list[str]
