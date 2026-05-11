from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import crud
from app.db.session import get_db
from app.deps.auth import CurrentUser, get_current_user
from app.schemas import (
    ChatMessageIn,
    ChatMessageOut,
    ChatReplyOut,
    ChatSessionOut,
    ChatToolAction,
)
from app.services.chat.onboarding import run_onboarding_step
from app.services.chat.onboarding_semester_plan_job import (
    run_onboarding_semester_plan_job,
)
from app.services.datetime_parse import parse_user_due_to_datetime

router = APIRouter(prefix="/chat", tags=["chat"])


def _user_uuid(user: CurrentUser) -> uuid.UUID:
    try:
        return uuid.UUID(user.user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user id")


def _onboarding_done(state_json: dict[str, Any]) -> bool:
    return bool(state_json.get("complete")) or bool(
        state_json.get("onboarding_complete")
    )


def _chat_reply_fields(
    state_json: dict[str, Any],
) -> tuple[bool, uuid.UUID | None, str | None]:
    complete = _onboarding_done(state_json)
    raw_class_id = state_json.get("class_id")
    out_class_id: uuid.UUID | None = None
    if isinstance(raw_class_id, str):
        try:
            out_class_id = uuid.UUID(raw_class_id)
        except ValueError:
            out_class_id = None
    next_url = f"/classes/{out_class_id}" if complete and out_class_id else None
    return complete, out_class_id, next_url


@router.post("/sessions", response_model=ChatSessionOut)
def create_or_get_session(
    force_new: bool = Query(
        False, description="If true, always start a new onboarding session."
    ),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSessionOut:
    user_id = _user_uuid(user)
    if force_new:
        crud.archive_active_chat_sessions(db=db, user_id=user_id)
        created = crud.create_chat_session(db=db, user_id=user_id)
        return ChatSessionOut.model_validate(created)

    existing = crud.get_active_chat_session(db=db, user_id=user_id)
    if existing is not None:
        return ChatSessionOut.model_validate(existing)
    created = crud.create_chat_session(db=db, user_id=user_id)
    return ChatSessionOut.model_validate(created)


@router.get("/sessions/{session_id}", response_model=ChatReplyOut)
def get_session(
    session_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatReplyOut:
    user_id = _user_uuid(user)
    sess = crud.get_chat_session(db=db, user_id=user_id, session_id=session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    msgs = crud.list_chat_messages(db=db, user_id=user_id, session_id=session_id)
    st = crud.get_chat_state(db=db, user_id=user_id, session_id=session_id)
    state_json: dict[str, Any] = st.state_json if st is not None else {}
    complete, out_class_id, next_url = _chat_reply_fields(state_json)
    return ChatReplyOut(
        session=ChatSessionOut.model_validate(sess),
        messages=[ChatMessageOut.model_validate(m) for m in msgs],
        state=state_json,
        tool_actions=[],
        complete=complete,
        class_id=out_class_id,
        next_url=next_url,
    )


@router.post("/sessions/{session_id}/messages", response_model=ChatReplyOut)
def post_message(
    session_id: uuid.UUID,
    payload: ChatMessageIn,
    background_tasks: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatReplyOut:
    user_id = _user_uuid(user)
    sess = crud.get_chat_session(db=db, user_id=user_id, session_id=session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    st = crud.get_chat_state(db=db, user_id=user_id, session_id=session_id)
    state_json: dict[str, Any] = st.state_json if st is not None else {}

    # Persist user message
    crud.add_chat_message(
        db=db,
        user_id=user_id,
        session_id=session_id,
        role="user",
        content=payload.content,
    )

    onboarding = run_onboarding_step(state=state_json, user_message=payload.content)
    state_json = onboarding.state

    # Execute tool actions (wizard orchestrator).
    class_id: uuid.UUID | None = None
    for action in onboarding.tool_actions:
        a_type = str(action.get("type") or "")
        payload_raw = action.get("payload")
        payload_obj: dict[str, Any] = (
            payload_raw if isinstance(payload_raw, dict) else {}
        )

        if a_type == "create_class":
            title_raw = payload_obj.get("title")
            if isinstance(title_raw, str) and title_raw.strip():
                created = crud.create_class(
                    db=db, user_id=user_id, title=title_raw.strip()
                )
                class_id = created.id
                state_json["class_id"] = str(created.id)

        elif a_type == "set_class_timeline":
            raw_class_id = state_json.get("class_id")
            if isinstance(raw_class_id, str):
                try:
                    class_id = uuid.UUID(raw_class_id)
                except ValueError:
                    class_id = None
            if class_id is not None:
                availability = payload_obj.get("availability")
                availability_json = None
                if isinstance(availability, list):
                    availability_json = {"blocks": availability}
                crud.update_class_timeline(
                    db=db,
                    user_id=user_id,
                    class_id=class_id,
                    semester_start=(
                        payload_obj.get("semester_start")
                        if isinstance(payload_obj.get("semester_start"), str)
                        else None
                    ),
                    semester_end=(
                        payload_obj.get("semester_end")
                        if isinstance(payload_obj.get("semester_end"), str)
                        else None
                    ),
                    timezone=(
                        payload_obj.get("timezone")
                        if isinstance(payload_obj.get("timezone"), str)
                        else None
                    ),
                    availability_json=availability_json,
                )

        elif a_type == "create_deadline":
            raw_class_id = state_json.get("class_id")
            if isinstance(raw_class_id, str):
                try:
                    class_id = uuid.UUID(raw_class_id)
                except ValueError:
                    class_id = None
            if class_id is not None:
                title_raw = payload_obj.get("title")
                due_text = payload_obj.get("due_text")
                if isinstance(title_raw, str) and isinstance(due_text, str):
                    tz = (
                        state_json.get("timezone")
                        if isinstance(state_json.get("timezone"), str)
                        else None
                    )
                    due_at = parse_user_due_to_datetime(due=due_text, timezone=tz)
                    crud.create_deadline(
                        db=db,
                        user_id=user_id,
                        class_id=class_id,
                        title=title_raw,
                        due_text=due_text,
                        due_at=due_at,
                    )

        elif a_type == "generate_semester_plan":
            raw_class_id = state_json.get("class_id")
            if isinstance(raw_class_id, str):
                try:
                    class_id = uuid.UUID(raw_class_id)
                except ValueError:
                    class_id = None
            if class_id is not None:
                clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
                if clazz is None:
                    continue
                semester_start = state_json.get("semester_start")
                semester_end = state_json.get("semester_end")
                tz = state_json.get("timezone")
                if not (
                    isinstance(semester_start, str)
                    and isinstance(semester_end, str)
                    and isinstance(tz, str)
                ):
                    continue
                if state_json.get("semester_plan_status") == "generating":
                    continue
                state_json["semester_plan_status"] = "generating"
                state_json.pop("semester_plan_error", None)
                background_tasks.add_task(
                    run_onboarding_semester_plan_job,
                    user_id=user_id,
                    session_id=session_id,
                    class_id=class_id,
                )

        elif a_type == "complete":
            state_json["complete"] = True

    crud.update_chat_state(
        db=db, user_id=user_id, session_id=session_id, state_json=state_json
    )

    # Persist assistant message
    crud.add_chat_message(
        db=db,
        user_id=user_id,
        session_id=session_id,
        role="assistant",
        content=onboarding.assistant_message,
    )

    msgs = crud.list_chat_messages(db=db, user_id=user_id, session_id=session_id)
    complete, out_class_id, next_url = _chat_reply_fields(state_json)

    return ChatReplyOut(
        session=ChatSessionOut.model_validate(sess),
        messages=[ChatMessageOut.model_validate(m) for m in msgs],
        state=state_json,
        tool_actions=[
            ChatToolAction(
                type=str(a.get("type", "unknown")),
                payload=dict(a.get("payload", {}) or {}),
            )
            for a in onboarding.tool_actions
        ],
        complete=complete,
        class_id=out_class_id,
        next_url=next_url,
    )
