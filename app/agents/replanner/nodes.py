from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.agents.replanner.state import ReplannerState
from app.core.config import get_settings
from app.db import crud
from app.db.session import get_engine
from app.services.study_plan_semester import generate_semester_study_plan

logger = logging.getLogger("gradepilot.replanner")


def _utc_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _parse_dt(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _deadline_payload(deadlines: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for d in deadlines:
        out.append(
            {
                "id": str(d.id),
                "title": str(d.title),
                "due_text": str(d.due_text),
                "due_at": _utc_iso(getattr(d, "due_at", None)),
                "completed_at": _utc_iso(getattr(d, "completed_at", None)),
                "created_at": _utc_iso(getattr(d, "created_at", None)),
            }
        )
    return out


def _extract_deadline_ids_from_plan(plan_json: dict[str, Any]) -> set[str]:
    refs: set[str] = set()

    def _walk(obj: object) -> None:
        if isinstance(obj, dict):
            if "deadline_id" in obj and isinstance(obj["deadline_id"], str):
                refs.add(obj["deadline_id"])
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(plan_json)

    # Optional snapshot of deadlines (if present).
    deadlines = plan_json.get("deadlines")
    if isinstance(deadlines, list):
        for d in deadlines:
            if isinstance(d, dict) and isinstance(d.get("id"), str):
                refs.add(d["id"])
    return refs


def _extract_deadline_snapshot(plan_json: dict[str, Any]) -> dict[str, datetime | None]:
    """Best-effort id->due_at snapshot from stored plan_json."""
    snapshot: dict[str, datetime | None] = {}
    deadlines = plan_json.get("deadlines")
    if not isinstance(deadlines, list):
        return snapshot
    for d in deadlines:
        if not isinstance(d, dict):
            continue
        did = d.get("id")
        if not isinstance(did, str):
            continue
        snapshot[did] = _parse_dt(d.get("due_at"))
    return snapshot


def _make_session() -> Session:
    # Keep this local to avoid importing app.db.session internals.
    engine = get_engine()
    SessionLocal: sessionmaker[Session] = sessionmaker(
        bind=engine, autocommit=False, autoflush=False
    )
    return SessionLocal()


def load_context(state: ReplannerState) -> ReplannerState:
    try:
        user_id = uuid.UUID(state["user_id"])
        class_id = uuid.UUID(state["class_id"])
    except ValueError:
        state["errors"].append("Invalid user_id or class_id")
        return state

    db = _make_session()
    try:
        clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
        if clazz is None:
            state["errors"].append("Class not found")
            return state

        deadlines = crud.list_deadlines(db=db, user_id=user_id, class_id=class_id)
        latest_plan = crud.get_latest_study_plan(
            db=db, user_id=user_id, class_id=class_id
        )
        notes = crud.list_notes(db=db, user_id=user_id, class_id=class_id)
        user_settings = crud.get_user_settings(db=db, user_id=user_id)
        integ = crud.get_google_integration(db=db, user_id=user_id)

        state["class_data"] = {
            "id": str(clazz.id),
            "title": clazz.title,
            "semester_start": clazz.semester_start,
            "semester_end": clazz.semester_end,
            "timezone": clazz.timezone,
            "availability_json": clazz.availability_json,
            "created_at": _utc_iso(clazz.created_at),
        }
        state["deadlines"] = _deadline_payload(deadlines)
        state["latest_plan"] = (
            {
                "id": str(latest_plan.id),
                "created_at": _utc_iso(latest_plan.created_at),
                "plan_json": dict(latest_plan.plan_json),
                "model": latest_plan.model,
            }
            if latest_plan is not None
            else None
        )
        state["notes"] = [
            {
                "id": str(n.id),
                "created_at": _utc_iso(n.created_at),
                "notes_text": n.notes_text,
            }
            for n in notes
        ]
        state["user_settings"] = (
            {
                "notifications_enabled": user_settings.notifications_enabled,
                "days_before_deadline": user_settings.days_before_deadline,
                "timezone": user_settings.timezone,
                # Additive: used by schedule_study_session. The existing
                # auto_sync_calendar key (read by graph.should_sync_calendar)
                # is intentionally NOT added here -- that gate continues to
                # rely on sync_calendar_override exactly as before.
                "auto_schedule_sessions": bool(user_settings.auto_schedule_sessions),
                "preferred_study_windows": list(
                    user_settings.preferred_study_windows or []
                ),
            }
            if user_settings is not None
            else {}
        )
        state["has_google_integration"] = integ is not None
    except Exception as e:  # noqa: BLE001
        state["errors"].append(f"load_context_failed:{e.__class__.__name__}")
    finally:
        db.close()
    return state


def should_replan_gate(state: ReplannerState) -> ReplannerState:
    signals: dict[str, Any] = {}
    state["change_signals"] = signals

    if state.get("force_replan", False):
        state["should_replan"] = True
        state["replan_reason"] = "forced"
        signals["forced"] = True
        return state

    latest = state.get("latest_plan")
    if latest is None:
        state["should_replan"] = True
        state["replan_reason"] = "no_existing_plan"
        signals["no_existing_plan"] = True
        return state

    trigger = state.get("trigger")
    if trigger == "progress_updated":
        state["should_replan"] = False
        state["replan_reason"] = "progress_only"
        signals["progress_only"] = True
        return state

    latest_created_at = _parse_dt(latest.get("created_at"))

    if trigger == "notes_added":
        notes = state.get("notes") or []
        newer = False
        for n in notes:
            n_dt = _parse_dt(n.get("created_at") if isinstance(n, dict) else None)
            if (
                n_dt is not None
                and latest_created_at is not None
                and n_dt > latest_created_at
            ):
                newer = True
                break
            if n_dt is not None and latest_created_at is None:
                newer = True
                break
        signals["notes_newer_than_plan"] = newer
        if newer:
            state["should_replan"] = True
            state["replan_reason"] = "notes_newer_than_plan"
            return state

    if trigger in {"deadline_imported", "deadline_added", "manual_replan"}:
        plan_json = latest.get("plan_json")
        if isinstance(plan_json, dict):
            referenced = _extract_deadline_ids_from_plan(plan_json)
            snapshot = _extract_deadline_snapshot(plan_json)
        else:
            referenced = set()
            snapshot = {}

        current_deadlines = state.get("deadlines") or []
        current_ids = {
            d.get("id")
            for d in current_deadlines
            if isinstance(d, dict) and isinstance(d.get("id"), str)
        }
        current_ids_str = {str(x) for x in current_ids if x is not None}
        referenced_ids_str = {str(x) for x in referenced if x is not None}

        new_ids = sorted(current_ids_str - referenced_ids_str)
        deleted_ids = sorted(referenced_ids_str - current_ids_str)
        signals["new_deadlines"] = len(new_ids)
        signals["deleted_deadlines"] = len(deleted_ids)

        shifted: list[dict[str, Any]] = []
        if snapshot:
            by_id: dict[str, dict[str, Any]] = {
                str(d["id"]): d
                for d in current_deadlines
                if isinstance(d, dict) and isinstance(d.get("id"), str)
            }
            for did, prev_due in snapshot.items():
                cur = by_id.get(did)
                cur_due = _parse_dt(cur.get("due_at")) if cur else None
                if prev_due is None or cur_due is None:
                    continue
                delta_days = abs((cur_due.date() - prev_due.date()).days)
                if delta_days >= 2:
                    shifted.append({"id": did, "delta_days": delta_days})
        signals["shifted_deadlines"] = len(shifted)
        if shifted:
            signals["shifted_deadline_details"] = shifted[:25]

        if new_ids:
            state["should_replan"] = True
            state["replan_reason"] = f"new_deadlines:{len(new_ids)}"
            return state
        if deleted_ids:
            state["should_replan"] = True
            state["replan_reason"] = f"deadlines_deleted:{len(deleted_ids)}"
            return state
        if shifted:
            state["should_replan"] = True
            state["replan_reason"] = f"deadlines_shifted:{len(shifted)}"
            return state

    state["should_replan"] = False
    state["replan_reason"] = "no_material_change"
    return state


def generate_plan(state: ReplannerState) -> ReplannerState:
    clazz = state.get("class_data")
    if not isinstance(clazz, dict):
        state["errors"].append("missing_class_data")
        return state

    semester_start = clazz.get("semester_start")
    semester_end = clazz.get("semester_end")
    timezone = clazz.get("timezone")
    title = clazz.get("title")

    if not all(
        isinstance(v, str) and v.strip()
        for v in [semester_start, semester_end, timezone, title]
    ):
        state["errors"].append("missing_timeline_fields")
        return state

    deadlines = state.get("deadlines") or []
    availability_json = clazz.get("availability_json")
    availability: list[dict[str, str]] | None = None
    if isinstance(availability_json, dict):
        blocks = availability_json.get("blocks")
        if isinstance(blocks, list):
            availability = [b for b in blocks if isinstance(b, dict)]

    carried: list[Any] | None = None
    latest = state.get("latest_plan")
    if isinstance(latest, dict):
        pj = latest.get("plan_json")
        if isinstance(pj, dict) and isinstance(pj.get("completed_tasks"), list):
            carried = list(pj["completed_tasks"])

    try:
        plan_json, model = generate_semester_study_plan(
            class_title=str(title),
            semester_start=str(semester_start),
            semester_end=str(semester_end),
            timezone=str(timezone),
            deadlines=[d for d in deadlines if isinstance(d, dict)],
            availability=availability,
        )
        if carried is not None:
            plan_json = dict(plan_json)
            plan_json["completed_tasks"] = carried
            state["completed_tasks_carried"] = carried
        state["new_plan"] = plan_json
        state["change_signals"] = dict(state.get("change_signals") or {}, model=model)
    except Exception as e:  # noqa: BLE001
        state["errors"].append(f"generate_plan_failed:{e.__class__.__name__}")
    return state


def persist_plan(state: ReplannerState) -> ReplannerState:
    if state.get("dry_run", False):
        return state

    new_plan = state.get("new_plan")
    if not isinstance(new_plan, dict):
        state["errors"].append("missing_new_plan")
        return state

    try:
        user_id = uuid.UUID(state["user_id"])
        class_id = uuid.UUID(state["class_id"])
    except ValueError:
        state["errors"].append("Invalid user_id or class_id")
        return state

    model_name = str((state.get("change_signals") or {}).get("model") or "unknown")

    db = _make_session()
    try:
        plan = crud.create_study_plan(
            db=db,
            user_id=user_id,
            class_id=class_id,
            source_notes_id=None,
            plan_json=new_plan,
            model=model_name,
        )
        state["new_plan_id"] = str(plan.id)
    except Exception as e:  # noqa: BLE001
        state["errors"].append(f"persist_plan_failed:{e.__class__.__name__}")
    finally:
        db.close()
    return state


def sync_calendar(state: ReplannerState) -> ReplannerState:
    if state.get("dry_run", False):
        return state

    try:
        from app.services.google_calendar import (
            sync_class,
        )  # local import to avoid cycles
    except Exception as e:  # noqa: BLE001
        state["errors"].append(f"sync_calendar_import_failed:{e.__class__.__name__}")
        return state

    try:
        user_id = uuid.UUID(state["user_id"])
        class_id = uuid.UUID(state["class_id"])
    except ValueError:
        state["errors"].append("Invalid user_id or class_id")
        return state

    db = _make_session()
    try:
        settings = get_settings()
        res = sync_class(db=db, user_id=user_id, class_id=class_id, settings=settings)
        state["calendar_sync_result"] = res
    except Exception as e:  # noqa: BLE001
        state["errors"].append(f"sync_calendar_failed:{e.__class__.__name__}")
    finally:
        db.close()
    return state


def schedule_study_session(state: ReplannerState) -> ReplannerState:
    """Auto-pick a 60-min slot in the user's calendar and create the event.

    Only runs on ``notes_added`` triggers and only when the user has opted in
    via ``user_settings.auto_schedule_sessions``. All failure modes (missing
    integration, insufficient scopes, no slot available, Google API error)
    push to ``state["errors"]`` rather than raising.
    """
    forced = bool(state.get("force_schedule_session", False))
    if state.get("trigger") != "notes_added" and not forced:
        return state
    if state.get("dry_run", False):
        return state

    settings_dict = state.get("user_settings") or {}
    if not forced and not bool(settings_dict.get("auto_schedule_sessions", False)):
        return state

    if not state.get("has_google_integration", False):
        logger.info("schedule_study_session: skipped (no google integration)")
        if forced:
            state["errors"].append("schedule_study_session_skip:no_google_integration")
        return state

    notes_list = state.get("notes") or []
    if not notes_list:
        logger.info("schedule_study_session: skipped (no notes in state)")
        if forced:
            state["errors"].append("schedule_study_session_skip:no_notes")
        return state
    latest_note = notes_list[0]
    if not isinstance(latest_note, dict) or not isinstance(latest_note.get("id"), str):
        return state

    class_data = state.get("class_data")
    if not isinstance(class_data, dict):
        return state

    user_tz = settings_dict.get("timezone") or class_data.get("timezone") or "UTC"
    if not isinstance(user_tz, str) or not user_tz.strip():
        user_tz = "UTC"

    preferred_windows_raw = settings_dict.get("preferred_study_windows") or []
    preferred_windows: list[dict[str, str]] = [
        w
        for w in preferred_windows_raw
        if isinstance(w, dict)
        and isinstance(w.get("start"), str)
        and isinstance(w.get("end"), str)
    ]

    # Local imports keep the graph importable even when scheduling deps fail
    # to import for any reason (e.g. zoneinfo data missing in a stripped image).
    try:
        from app.services.google_calendar import (
            create_study_session_event,
            has_required_scopes,
            list_busy_blocks,
        )
        from app.services.scheduling.anchors import compute_next_anchor
        from app.services.scheduling.slot_finder import find_first_available_slot
    except Exception as e:  # noqa: BLE001
        state["errors"].append(
            f"schedule_study_session_import_failed:{e.__class__.__name__}"
        )
        return state

    db = _make_session()
    try:
        try:
            user_uuid = uuid.UUID(state["user_id"])
            class_uuid = uuid.UUID(state["class_id"])
            notes_uuid = uuid.UUID(latest_note["id"])
        except (KeyError, ValueError):
            state["errors"].append("schedule_study_session_invalid_ids")
            return state

        integ = crud.get_google_integration(db=db, user_id=user_uuid)
        if integ is None:
            logger.info("schedule_study_session: skipped (no google integration in DB)")
            if forced:
                state["errors"].append(
                    "schedule_study_session_skip:no_google_integration"
                )
            return state
        if not has_required_scopes(integ):
            logger.info(
                "schedule_study_session: skipped (insufficient scopes; "
                "user must reconnect Google)"
            )
            if forced:
                state["errors"].append(
                    "schedule_study_session_skip:insufficient_scopes"
                )
            return state

        now = datetime.now(timezone.utc)

        try:
            anchor = compute_next_anchor(
                class_data=class_data,
                deadlines=[
                    d for d in (state.get("deadlines") or []) if isinstance(d, dict)
                ],
                from_dt=now,
            )
        except Exception as e:  # noqa: BLE001
            state["errors"].append(
                f"schedule_study_session_anchor_failed:{e.__class__.__name__}"
            )
            return state

        if anchor.at <= now:
            logger.info("schedule_study_session: anchor in the past; nothing to do")
            if forced:
                state["errors"].append("schedule_study_session_skip:anchor_in_past")
            return state

        try:
            busy_blocks = list_busy_blocks(
                db=db,
                user_id=str(user_uuid),
                start=now,
                end=anchor.at,
            )
        except Exception as e:  # noqa: BLE001
            state["errors"].append(
                f"schedule_study_session_busy_failed:{e.__class__.__name__}"
            )
            return state

        try:
            slot = find_first_available_slot(
                busy_blocks=busy_blocks,
                preferred_windows=preferred_windows,
                user_timezone=user_tz,
                search_start=now,
                search_end=anchor.at,
            )
        except Exception as e:  # noqa: BLE001
            state["errors"].append(
                f"schedule_study_session_slot_failed:{e.__class__.__name__}"
            )
            return state

        if slot is None:
            logger.info(
                "schedule_study_session: no slot found before anchor=%s",
                anchor.at.isoformat(),
            )
            if forced:
                state["errors"].append("schedule_study_session_skip:no_slot_found")
            return state

        title = f"Study: {class_data.get('title') or 'class'}"
        description = (
            f"Anchor: {anchor.kind} at {anchor.at.isoformat()}.\n"
            "Created on the GradePilot calendar; safe to move or delete."
        )

        try:
            event = create_study_session_event(
                db=db,
                user_id=str(user_uuid),
                class_id=class_uuid,
                notes_id=notes_uuid,
                title=title,
                start=slot.start,
                end=slot.end,
                description=description,
            )
        except Exception as e:  # noqa: BLE001
            state["errors"].append(
                f"schedule_study_session_create_failed:{e.__class__.__name__}"
            )
            return state

        state["scheduled_session"] = {
            "start": slot.start.isoformat(),
            "end": slot.end.isoformat(),
            "in_preferred_window": slot.in_preferred_window,
            "calendar_event_link": event.get("html_link", ""),
            "calendar_event_id": event.get("event_id", ""),
            "anchor_kind": anchor.kind,
        }
    finally:
        db.close()
    return state


def finalize(state: ReplannerState) -> ReplannerState:
    return state
