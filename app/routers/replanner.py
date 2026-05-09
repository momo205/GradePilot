from __future__ import annotations

import logging
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.replanner.graph import ReplannerInput, run_replanner
from app.db import crud
from app.db.session import get_db
from app.deps.auth import CurrentUser, get_current_user

logger = logging.getLogger("gradepilot.replanner")

router = APIRouter(prefix="/classes", tags=["replanner"])


def _user_uuid(user: CurrentUser) -> uuid.UUID:
    try:
        return uuid.UUID(user.user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user id")


Trigger = Literal[
    "onboarding",
    "deadline_imported",
    "deadline_added",
    "notes_added",
    "progress_updated",
    "manual_replan",
]


class ReplanRequest(BaseModel):
    trigger: Trigger
    dry_run: bool = False
    force_replan: bool = False
    sync_calendar_override: bool | None = None
    # When True, run schedule_study_session even if the user has not opted in
    # via auto_schedule_sessions and even if the trigger is not notes_added.
    # Used by the dashboard "Schedule study session now" button.
    force_schedule_session: bool = False


@router.post("/{class_id}/replan")
async def replan_class(
    class_id: uuid.UUID,
    payload: ReplanRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user_id = _user_uuid(user)

    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")

    thread_id = f"{user.user_id}:{class_id}"
    inp: ReplannerInput = {
        "user_id": user.user_id,
        "class_id": str(class_id),
        "trigger": payload.trigger,
        "dry_run": payload.dry_run,
        "force_replan": payload.force_replan,
        "sync_calendar_override": payload.sync_calendar_override,
        "force_schedule_session": payload.force_schedule_session,
    }

    try:
        out = await run_replanner(inp, thread_id=thread_id)
    except Exception as e:  # noqa: BLE001
        logger.exception("replan_failed err=%s", e.__class__.__name__)
        raise HTTPException(status_code=502, detail="Replanner failed") from e

    return {
        "should_replan": out.get("should_replan"),
        "replan_reason": out.get("replan_reason"),
        "change_signals": out.get("change_signals"),
        "new_plan_id": out.get("new_plan_id"),
        "new_plan": out.get("new_plan"),
        "calendar_sync_result": out.get("calendar_sync_result"),
        "scheduled_session": out.get("scheduled_session"),
        "scheduled_plan_sessions": out.get("scheduled_plan_sessions") or [],
        "errors": out.get("errors", []),
    }
