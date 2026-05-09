from __future__ import annotations

import asyncio
import os
from typing import Any, Literal, NotRequired, Optional, TypedDict, cast

from langgraph.graph import END, START, StateGraph

from app.agents.replanner.nodes import (
    finalize,
    generate_plan,
    load_context,
    persist_plan,
    schedule_plan_sessions,
    schedule_study_session,
    should_replan_gate,
    sync_calendar,
)
from app.agents.replanner.state import ReplannerState
from app.core.config import get_settings

_PostgresSaver: Any = None
try:
    # Provided by `langgraph-checkpoint-postgres`.
    from langgraph.checkpoint.postgres import PostgresSaver as _ImportedPostgresSaver

    _PostgresSaver = _ImportedPostgresSaver
    _HAS_POSTGRES_CHECKPOINTER = True
except Exception:  # pragma: no cover
    _HAS_POSTGRES_CHECKPOINTER = False


def _should_use_postgres_checkpointer(conn_str: str) -> bool:
    """PostgresSaver holds a psycopg connection; only use it for real Postgres DSNs."""
    if not conn_str or not _HAS_POSTGRES_CHECKPOINTER or _PostgresSaver is None:
        return False
    scheme = conn_str.split("://", 1)[0].lower()
    if scheme.startswith("sqlite"):
        return False
    return "postgres" in scheme


Trigger = Literal[
    "onboarding",
    "deadline_imported",
    "deadline_added",
    "notes_added",
    "progress_updated",
    "manual_replan",
]


class ReplannerInput(TypedDict):
    user_id: str
    class_id: str
    trigger: Trigger
    dry_run: bool
    force_replan: bool
    sync_calendar_override: Optional[bool]
    force_schedule_session: NotRequired[bool]


def should_sync_calendar(state: ReplannerState) -> bool:
    override = state.get("sync_calendar_override")
    if override is not None:
        return bool(override)

    if not state.get("has_google_integration", False):
        return False

    settings = state.get("user_settings") or {}
    if not isinstance(settings, dict):
        return False
    return bool(settings.get("auto_sync_calendar", False))


def build_graph(*, checkpointer: Any | None = None) -> Any:
    graph = StateGraph(ReplannerState)
    graph.add_node("load_context", load_context)
    graph.add_node("should_replan_gate", should_replan_gate)
    graph.add_node("generate_plan", generate_plan)
    graph.add_node("persist_plan", persist_plan)
    graph.add_node("schedule_plan_sessions", schedule_plan_sessions)
    graph.add_node("schedule_study_session", schedule_study_session)
    graph.add_node("sync_calendar", sync_calendar)
    graph.add_node("finalize", finalize)

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "should_replan_gate")

    def _replan_branch(s: ReplannerState) -> str:
        if s.get("should_replan"):
            return "replan"
        # Even when nothing changed enough to warrant a new plan, a manual
        # "Schedule now" click should still try to book a study session.
        if s.get("force_schedule_session", False):
            return "schedule_only"
        return "skip"

    graph.add_conditional_edges(
        "should_replan_gate",
        _replan_branch,
        {
            "skip": "finalize",
            "replan": "generate_plan",
            "schedule_only": "schedule_study_session",
        },
    )
    graph.add_edge("generate_plan", "persist_plan")

    # Calendar-sync gate (unchanged; intentionally still keyed off the legacy
    # auto_sync_calendar / sync_calendar_override path). Reused after both
    # persist_plan and schedule_study_session.
    def _sync_branch(s: ReplannerState) -> str:
        return "sync" if should_sync_calendar(s) else "nosync"

    # After persist_plan, route through scheduling whenever notes_added (or any
    # manual force-schedule request) brought us here. The flow is now
    # persist_plan -> schedule_plan_sessions -> schedule_study_session ->
    # sync_calendar gate, so the user gets:
    #   * one calendar block per day in the new plan (plan-day sessions), and
    #   * a single focused-study session anchored to the next lecture.
    # Other triggers (deadline_added, etc.) keep the original sync-only path.
    def _post_persist_branch(s: ReplannerState) -> str:
        if s.get("trigger") == "notes_added" or s.get("force_schedule_session", False):
            return "schedule"
        return _sync_branch(s)

    graph.add_conditional_edges(
        "persist_plan",
        _post_persist_branch,
        {
            "schedule": "schedule_plan_sessions",
            "sync": "sync_calendar",
            "nosync": "finalize",
        },
    )
    graph.add_edge("schedule_plan_sessions", "schedule_study_session")
    graph.add_conditional_edges(
        "schedule_study_session",
        _sync_branch,
        {"sync": "sync_calendar", "nosync": "finalize"},
    )
    graph.add_edge("sync_calendar", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile(checkpointer=checkpointer)


replanner_graph = build_graph()


def _run_replanner_sync(inp: ReplannerInput, thread_id: str | None) -> ReplannerState:
    """Run the graph in one thread (required when using psycopg-based checkpointer)."""
    _ = get_settings()

    state: ReplannerState = {
        "user_id": inp["user_id"],
        "class_id": inp["class_id"],
        "trigger": inp["trigger"],
        "dry_run": bool(inp.get("dry_run", False)),
        "force_replan": bool(inp.get("force_replan", False)),
        "sync_calendar_override": inp.get("sync_calendar_override"),
        "force_schedule_session": bool(inp.get("force_schedule_session", False)),
        "class_data": None,
        "deadlines": None,
        "latest_plan": None,
        "notes": None,
        "user_settings": None,
        "has_google_integration": False,
        "should_replan": None,
        "replan_reason": None,
        "change_signals": None,
        "new_plan": None,
        "new_plan_id": None,
        "calendar_sync_result": None,
        "completed_tasks_carried": None,
        "scheduled_session": None,
        "scheduled_plan_sessions": None,
        "errors": [],
    }

    config: dict[str, Any] = {}
    if thread_id is not None:
        config = {"configurable": {"thread_id": thread_id}}

    conn_str = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL") or ""
    if _should_use_postgres_checkpointer(conn_str) and _PostgresSaver is not None:
        with _PostgresSaver.from_conn_string(conn_str) as checkpointer:
            checkpointer.setup()
            graph = build_graph(checkpointer=checkpointer)
            out = cast(Any, graph).invoke(state, config=config)
            return cast(ReplannerState, out)

    out = cast(Any, replanner_graph).invoke(state, config=config)
    return cast(ReplannerState, out)


async def run_replanner(
    input: ReplannerInput, thread_id: str | None = None
) -> ReplannerState:
    return await asyncio.to_thread(_run_replanner_sync, input, thread_id)
