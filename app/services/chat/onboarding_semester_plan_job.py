"""Background execution of semester study plan generation (onboarding phase 4)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db import crud
from app.db.session import session_scope
from app.services.study_plan_semester import (
    SemesterStudyPlanGenerationError,
    SemesterStudyPlanRateLimitError,
    generate_semester_study_plan,
)

logger = logging.getLogger("gradepilot.chat")


def run_onboarding_semester_plan_job(
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    class_id: uuid.UUID,
) -> None:
    """Persist semester plan and mark onboarding complete; runs outside the HTTP request."""
    with session_scope() as db:
        st = crud.get_chat_state(db=db, user_id=user_id, session_id=session_id)
        if st is None:
            logger.warning("onboarding_semester_plan_missing_chat_state session=%s", session_id)
            return

        state_json: dict[str, Any] = dict(st.state_json or {})
        if state_json.get("semester_plan_status") != "generating":
            return

        clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
        if clazz is None:
            _fail_state(
                db=db,
                user_id=user_id,
                session_id=session_id,
                state_json=state_json,
                message="Class not found while generating the study plan.",
            )
            return

        deadlines = crud.list_deadlines(db=db, user_id=user_id, class_id=class_id)
        deadline_payload = [
            {
                "id": str(d.id),
                "title": d.title,
                "due_text": d.due_text,
                "due_at": (d.due_at.isoformat() if d.due_at else None),
            }
            for d in deadlines
        ]
        semester_start = state_json.get("semester_start")
        semester_end = state_json.get("semester_end")
        tz = state_json.get("timezone")
        availability = state_json.get("availability")
        if not (
            isinstance(semester_start, str)
            and isinstance(semester_end, str)
            and isinstance(tz, str)
        ):
            _fail_state(
                db=db,
                user_id=user_id,
                session_id=session_id,
                state_json=state_json,
                message="Missing semester dates or timezone for study plan generation.",
            )
            return

        try:
            plan_json, model_name = generate_semester_study_plan(
                class_title=clazz.title,
                semester_start=semester_start,
                semester_end=semester_end,
                timezone=tz,
                deadlines=deadline_payload,
                availability=availability if isinstance(availability, list) else None,
            )
        except SemesterStudyPlanRateLimitError as e:
            _fail_state(
                db=db,
                user_id=user_id,
                session_id=session_id,
                state_json=state_json,
                message=str(e),
            )
            return
        except SemesterStudyPlanGenerationError as e:
            _fail_state(
                db=db,
                user_id=user_id,
                session_id=session_id,
                state_json=state_json,
                message=str(e),
            )
            return
        except Exception:
            logger.exception("onboarding_semester_plan_unexpected_error")
            _fail_state(
                db=db,
                user_id=user_id,
                session_id=session_id,
                state_json=state_json,
                message="Study plan generation failed unexpectedly.",
            )
            return

        plan = crud.create_study_plan(
            db=db,
            user_id=user_id,
            class_id=class_id,
            source_notes_id=None,
            plan_json=plan_json,
            model=model_name,
        )
        state_json["latest_study_plan_id"] = str(plan.id)
        state_json["completed_at"] = datetime.now(UTC).isoformat()
        state_json["semester_plan_status"] = "done"
        state_json.pop("semester_plan_error", None)
        state_json["onboarding_complete"] = True
        state_json["complete"] = True
        crud.update_chat_state(
            db=db, user_id=user_id, session_id=session_id, state_json=state_json
        )


def _fail_state(
    *,
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    state_json: dict[str, Any],
    message: str,
) -> None:
    state_json["phase"] = 3
    state_json["semester_plan_status"] = "failed"
    state_json["semester_plan_error"] = message[:800]
    state_json.pop("onboarding_complete", None)
    state_json.pop("complete", None)
    crud.update_chat_state(
        db=db, user_id=user_id, session_id=session_id, state_json=state_json
    )
