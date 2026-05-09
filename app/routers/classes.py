from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.agents.replanner.graph import ReplannerInput, Trigger, run_replanner
from app.db import crud
from app.db.session import get_db
from app.deps.auth import CurrentUser, get_current_user
from app.schemas import (
    ClassCreate,
    ClassOut,
    ClassSummaryOut,
    ClassTimelineUpdate,
    DeadlineCreate,
    DeadlineOut,
    DeadlineImportOut,
    DeadlineUpdate,
    GradeBookState,
    NotesCreate,
    NotesOut,
    PracticeGenerateOut,
    PracticeGenerateRequest,
    StudyPlanCreate,
    StudyPlanOut,
    StudyPlanSemesterCreate,
    StudyPlanUpdate,
)
from app.services.datetime_parse import parse_user_due_to_datetime
from app.services.deadlines.extract import (
    DeadlineExtractError,
    DeadlineExtractRateLimitError,
    extract_deadlines_from_text,
)
from app.services.pdf_text import extract_text_from_pdf_bytes
from app.services.practice import (
    PracticeGenerationError,
    PracticeRateLimitError,
    generate_practice_questions,
)

# Per-lecture cap when building the practice prompt (avoids huge uploads).
_PRACTICE_NOTE_MAX_CHARS = 8000
from app.services.scheduling.anchors import compute_next_anchor
from app.services.scheduling.plan_sessions import schedule_plan_day_sessions
from app.services.study_plan import (
    StudyPlanGenerationError,
    StudyPlanRateLimitError,
    generate_study_plan,
)
from app.services.study_plan_semester import (
    SemesterStudyPlanGenerationError,
    SemesterStudyPlanRateLimitError,
    generate_semester_study_plan,
)

router = APIRouter(prefix="/classes", tags=["classes"])

logger = logging.getLogger("gradepilot.classes")


async def _fire_replanner_after_write(
    *,
    user: CurrentUser,
    class_id: uuid.UUID,
    trigger: Trigger,
) -> None:
    """Best-effort replan after a mutating write; failures are logged, not raised."""
    thread_id = f"{user.user_id}:{class_id}"
    inp: ReplannerInput = {
        "user_id": user.user_id,
        "class_id": str(class_id),
        "trigger": trigger,
        "dry_run": False,
        "force_replan": False,
        "sync_calendar_override": None,
    }
    try:
        await run_replanner(inp, thread_id=thread_id)
    except Exception:
        logger.exception(
            "replanner_hook_failed class_id=%s trigger=%s", class_id, trigger
        )


def _user_uuid(user: CurrentUser) -> uuid.UUID:
    try:
        return uuid.UUID(user.user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user id")


def _compute_plan_horizon(
    *,
    db: Session,
    user_id: uuid.UUID,
    class_id: uuid.UUID,
    clazz: Any,
) -> tuple[int, str]:
    """Return ``(horizon_days, horizon_reason)`` for the notes-driven plan.

    Uses the same ``compute_next_anchor`` used by the scheduler so the plan
    horizon, the auto-booked study session, and the user's mental model all
    agree on what "the next checkpoint" means: earliest of the next lecture
    (from ``meeting_pattern``), the next deadline, or a 7-day fallback.

    ``horizon_days`` is at least 1. Falls back to a 7-day "next checkpoint"
    if the anchor calculation cannot find anything (e.g. malformed timezone).
    """
    try:
        deadlines = crud.list_deadlines(db=db, user_id=user_id, class_id=class_id)
        deadline_payload: list[dict[str, Any]] = [
            {
                "id": str(d.id),
                "title": d.title,
                "due_text": d.due_text,
                "due_at": (d.due_at.isoformat() if d.due_at else None),
            }
            for d in deadlines
            if d.completed_at is None
        ]
        class_data: dict[str, Any] = {
            "title": clazz.title,
            "timezone": clazz.timezone,
            "semester_start": clazz.semester_start,
            "semester_end": clazz.semester_end,
            "meeting_pattern": clazz.meeting_pattern,
        }
        now = datetime.now(timezone.utc)
        anchor = compute_next_anchor(
            class_data=class_data,
            deadlines=deadline_payload,
            from_dt=now,
        )
        # Round UP so a lecture later today still yields a 1-day plan.
        delta_seconds = (anchor.at - now).total_seconds()
        days = max(1, math.ceil(delta_seconds / 86400.0))
        days = min(days, 14)
        if anchor.kind == "next_lecture":
            reason = (
                f"your next lecture on {anchor.at.strftime('%a %b %-d, %-I:%M %p %Z')}"
            )
        elif anchor.kind == "next_deadline":
            reason = (
                f"your next deadline on {anchor.at.strftime('%a %b %-d, %-I:%M %p %Z')}"
            )
        else:
            reason = "the next 7-day checkpoint"
        return days, reason
    except Exception:  # noqa: BLE001
        logger.exception("plan_horizon_failed class_id=%s", class_id)
        return 7, "the next checkpoint"


@router.get("", response_model=list[ClassOut])
def list_classes(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ClassOut]:
    classes = crud.list_classes(db=db, user_id=_user_uuid(user))
    return [ClassOut.model_validate(c) for c in classes]


@router.post("", response_model=ClassOut)
def create_class(
    payload: ClassCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClassOut:
    clazz = crud.create_class(db=db, user_id=_user_uuid(user), title=payload.title)
    return ClassOut.model_validate(clazz)


@router.get("/{class_id}", response_model=ClassSummaryOut)
def get_class_summary_endpoint(
    class_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClassSummaryOut:
    user_id = _user_uuid(user)
    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")

    deadlines = crud.list_deadlines(db=db, user_id=user_id, class_id=class_id)
    next_deadline = crud.get_next_deadline(db=db, user_id=user_id, class_id=class_id)
    latest_plan = crud.get_latest_study_plan(db=db, user_id=user_id, class_id=class_id)

    try:
        has_syllabus = crud.class_has_indexed_syllabus(
            db=db, user_id=user_id, class_id=class_id
        )
    except ProgrammingError:
        has_syllabus = False

    return ClassSummaryOut(
        clazz=ClassOut.model_validate(clazz),
        deadline_count=len(deadlines),
        next_deadline_id=(next_deadline.id if next_deadline else None),
        next_deadline_title=(next_deadline.title if next_deadline else None),
        next_deadline_due_at=(next_deadline.due_at if next_deadline else None),
        latest_study_plan_id=(latest_plan.id if latest_plan else None),
        latest_study_plan_created_at=(latest_plan.created_at if latest_plan else None),
        has_indexed_syllabus=has_syllabus,
    )


@router.patch("/{class_id}", response_model=ClassOut)
def update_class_timeline_endpoint(
    class_id: uuid.UUID,
    payload: ClassTimelineUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClassOut:
    user_id = _user_uuid(user)
    availability_json = (
        [
            {"day": b.day, "start_time": b.start_time, "end_time": b.end_time}
            for b in (payload.availability or [])
        ]
        if payload.availability is not None
        else None
    )
    meeting_pattern = (
        payload.meeting_pattern.model_dump() if payload.meeting_pattern else None
    )
    updated = crud.update_class_timeline(
        db=db,
        user_id=user_id,
        class_id=class_id,
        semester_start=payload.semester_start,
        semester_end=payload.semester_end,
        timezone=payload.timezone,
        availability_json=(
            {"blocks": availability_json} if availability_json is not None else None
        ),
        meeting_pattern=meeting_pattern,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Class not found")
    return ClassOut.model_validate(updated)


@router.put("/{class_id}/grade-book", response_model=GradeBookState)
def put_class_grade_book(
    class_id: uuid.UUID,
    payload: GradeBookState,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GradeBookState:
    user_id = _user_uuid(user)
    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")
    updated = crud.update_class_grade_book(
        db=db,
        user_id=user_id,
        class_id=class_id,
        grade_book=payload.model_dump(mode="json"),
    )
    if updated is None or updated.grade_book is None:
        raise HTTPException(status_code=500, detail="Failed to save grade book")
    return GradeBookState.model_validate(updated.grade_book)


@router.get("/{class_id}/notes", response_model=list[NotesOut])
def list_notes(
    class_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NotesOut]:
    user_id = _user_uuid(user)
    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")
    notes = crud.list_notes(db=db, user_id=user_id, class_id=class_id)
    return [NotesOut.model_validate(n) for n in notes]


@router.post("/{class_id}/notes", response_model=NotesOut)
async def add_notes(
    class_id: uuid.UUID,
    payload: NotesCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotesOut:
    user_id = _user_uuid(user)
    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")

    notes = crud.create_notes(
        db=db, user_id=user_id, class_id=class_id, notes_text=payload.notes_text
    )
    await _fire_replanner_after_write(
        user=user, class_id=class_id, trigger="notes_added"
    )
    return NotesOut.model_validate(notes)


@router.post("/{class_id}/practice", response_model=PracticeGenerateOut)
def generate_practice(
    class_id: uuid.UUID,
    payload: PracticeGenerateRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PracticeGenerateOut:
    user_id = _user_uuid(user)
    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")
    notes_list = crud.list_notes(db=db, user_id=user_id, class_id=class_id)
    if not notes_list:
        raise HTTPException(status_code=400, detail="No notes available for class")
    notes_ordered = sorted(notes_list, key=lambda n: n.created_at)
    segments: list[tuple[str, str]] = []
    for i, n in enumerate(notes_ordered, start=1):
        label = f"Lecture {i}"
        text = n.notes_text
        if len(text) > _PRACTICE_NOTE_MAX_CHARS:
            text = (
                text[:_PRACTICE_NOTE_MAX_CHARS]
                + "\n\n[...truncated for question generation]"
            )
        segments.append((label, text))
    try:
        questions = generate_practice_questions(
            class_title=clazz.title,
            note_segments=segments,
            count=payload.count,
            difficulty=payload.difficulty,
        )
    except PracticeRateLimitError as e:
        headers = {}
        if getattr(e, "retry_after_seconds", None):
            headers["Retry-After"] = str(e.retry_after_seconds)
        raise HTTPException(status_code=429, detail=str(e), headers=headers)
    except PracticeGenerationError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return PracticeGenerateOut(questions=questions)


@router.post("/{class_id}/study-plan", response_model=StudyPlanOut)
def create_study_plan_endpoint(
    class_id: uuid.UUID,
    payload: StudyPlanCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudyPlanOut:
    user_id = _user_uuid(user)
    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")

    if payload.notes_id is not None:
        notes = crud.get_notes(db=db, user_id=user_id, notes_id=payload.notes_id)
        if notes is None or notes.class_id != class_id:
            raise HTTPException(status_code=404, detail="Notes not found")
    else:
        notes = crud.get_latest_notes(db=db, user_id=user_id, class_id=class_id)
        if notes is None:
            raise HTTPException(status_code=400, detail="No notes available for class")

    horizon_days, horizon_reason = _compute_plan_horizon(
        db=db, user_id=user_id, class_id=class_id, clazz=clazz
    )

    try:
        plan_json, model_name = generate_study_plan(
            class_title=clazz.title,
            notes_text=notes.notes_text,
            horizon_days=horizon_days,
            horizon_reason=horizon_reason,
        )
    except StudyPlanRateLimitError as e:
        headers = {}
        if getattr(e, "retry_after_seconds", None):
            headers["Retry-After"] = str(e.retry_after_seconds)
        raise HTTPException(status_code=429, detail=str(e), headers=headers)
    except StudyPlanGenerationError as e:
        raise HTTPException(status_code=502, detail=str(e))

    plan = crud.create_study_plan(
        db=db,
        user_id=user_id,
        class_id=class_id,
        source_notes_id=notes.id,
        plan_json=plan_json,
        model=model_name,
    )

    # Best-effort: book one calendar block per plan day for users who have
    # opted into auto-scheduling. Failures here are logged but never bubbled,
    # so a Google outage cannot break plan creation. The booked sessions are
    # surfaced back to the client in the response so the dashboard can render
    # "N day blocks added to your calendar" without a second request.
    scheduled_sessions: list[dict[str, Any]] = []
    try:
        user_settings = crud.get_user_settings(db=db, user_id=user_id)
        if (
            user_settings is not None
            and bool(user_settings.auto_schedule_sessions)
            and crud.get_google_integration(db=db, user_id=user_id) is not None
        ):
            scheduled_sessions, _errors = schedule_plan_day_sessions(
                db=db,
                user_id=user_id,
                class_id=class_id,
                plan_id=plan.id,
                plan_json=plan_json,
                class_title=clazz.title,
                user_timezone=(user_settings.timezone or clazz.timezone or "UTC"),
                preferred_windows=list(user_settings.preferred_study_windows or []),
            )
    except Exception:
        logger.exception(
            "auto_schedule_plan_sessions_failed plan_id=%s class_id=%s",
            plan.id,
            class_id,
        )

    out = StudyPlanOut.model_validate(plan)
    out.scheduled_plan_sessions = scheduled_sessions
    return out


@router.post("/{class_id}/study-plan/semester", response_model=StudyPlanOut)
def create_semester_study_plan_endpoint(
    class_id: uuid.UUID,
    payload: StudyPlanSemesterCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudyPlanOut:
    user_id = _user_uuid(user)
    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")

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

    availability = (
        [
            {"day": b.day, "start_time": b.start_time, "end_time": b.end_time}
            for b in (payload.availability or [])
        ]
        if payload.availability
        else None
    )

    try:
        plan_json, model_name = generate_semester_study_plan(
            class_title=clazz.title,
            semester_start=payload.semester_start,
            semester_end=payload.semester_end,
            timezone=payload.timezone,
            deadlines=deadline_payload,
            availability=availability,
        )
    except SemesterStudyPlanRateLimitError as e:
        headers = {}
        if getattr(e, "retry_after_seconds", None):
            headers["Retry-After"] = str(e.retry_after_seconds)
        raise HTTPException(status_code=429, detail=str(e), headers=headers)
    except SemesterStudyPlanGenerationError as e:
        raise HTTPException(status_code=502, detail=str(e))

    plan = crud.create_study_plan(
        db=db,
        user_id=user_id,
        class_id=class_id,
        source_notes_id=None,
        plan_json=plan_json,
        model=model_name,
    )
    return StudyPlanOut.model_validate(plan)


@router.get("/{class_id}/study-plan/latest", response_model=StudyPlanOut)
def get_latest_study_plan_endpoint(
    class_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudyPlanOut:
    user_id = _user_uuid(user)
    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")
    plan = crud.get_latest_study_plan(db=db, user_id=user_id, class_id=class_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No study plan found")
    return StudyPlanOut.model_validate(plan)


@router.patch("/{class_id}/study-plan/{plan_id}", response_model=StudyPlanOut)
def update_study_plan_endpoint(
    class_id: uuid.UUID,
    plan_id: uuid.UUID,
    payload: StudyPlanUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StudyPlanOut:
    user_id = _user_uuid(user)
    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")

    updated = crud.update_study_plan_progress(
        db=db,
        user_id=user_id,
        class_id=class_id,
        plan_id=plan_id,
        completed_tasks=payload.completed_tasks,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Study plan not found")
    return StudyPlanOut.model_validate(updated)


@router.get("/{class_id}/deadlines", response_model=list[DeadlineOut])
def list_deadlines_endpoint(
    class_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DeadlineOut]:
    user_id = _user_uuid(user)
    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")
    deadlines = crud.list_deadlines(db=db, user_id=user_id, class_id=class_id)
    return [DeadlineOut.model_validate(d) for d in deadlines]


@router.post("/{class_id}/deadlines", response_model=DeadlineOut)
async def create_deadline_endpoint(
    class_id: uuid.UUID,
    payload: DeadlineCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeadlineOut:
    user_id = _user_uuid(user)
    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")
    due_at = parse_user_due_to_datetime(due=payload.due, timezone=clazz.timezone)
    created = crud.create_deadline(
        db=db,
        user_id=user_id,
        class_id=class_id,
        title=payload.title,
        due_text=payload.due,
        due_at=due_at,
    )
    await _fire_replanner_after_write(
        user=user, class_id=class_id, trigger="deadline_added"
    )
    return DeadlineOut.model_validate(created)


@router.patch("/{class_id}/deadlines/{deadline_id}", response_model=DeadlineOut)
def update_deadline_endpoint(
    class_id: uuid.UUID,
    deadline_id: uuid.UUID,
    payload: DeadlineUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeadlineOut:
    user_id = _user_uuid(user)
    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")

    if payload.completed is None:
        raise HTTPException(status_code=400, detail="No updates provided")

    completed_at = datetime.now(timezone.utc) if payload.completed else None
    updated = crud.update_deadline_completion(
        db=db,
        user_id=user_id,
        class_id=class_id,
        deadline_id=deadline_id,
        completed_at=completed_at,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return DeadlineOut.model_validate(updated)


@router.delete("/{class_id}/deadlines/{deadline_id}")
def delete_deadline_endpoint(
    class_id: uuid.UUID,
    deadline_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    user_id = _user_uuid(user)
    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")
    ok = crud.delete_deadline(
        db=db,
        user_id=user_id,
        class_id=class_id,
        deadline_id=deadline_id,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return {"ok": True}


@router.post("/{class_id}/deadlines/import", response_model=DeadlineImportOut)
async def import_deadlines_from_syllabus_endpoint(
    class_id: uuid.UUID,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeadlineImportOut:
    user_id = _user_uuid(user)
    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")

    name = (file.filename or "").strip() or "syllabus.pdf"
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if not name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Upload a .pdf file")

    try:
        raw_text = extract_text_from_pdf_bytes(data)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {e}") from e

    try:
        extracted = extract_deadlines_from_text(filename=name, raw_text=raw_text)
    except DeadlineExtractRateLimitError as e:
        headers = {}
        if getattr(e, "retry_after_seconds", None):
            headers["Retry-After"] = str(e.retry_after_seconds)
        raise HTTPException(status_code=429, detail=str(e), headers=headers)
    except DeadlineExtractError as e:
        status_code = int(getattr(e, "status_code", 502) or 502)
        raise HTTPException(status_code=status_code, detail=str(e))

    created = 0
    for d in extracted:
        crud.create_deadline(
            db=db,
            user_id=user_id,
            class_id=class_id,
            title=d.title,
            due_text=d.due_text,
            due_at=d.due_at,
        )
        created += 1

    if created > 0:
        await _fire_replanner_after_write(
            user=user, class_id=class_id, trigger="deadline_imported"
        )

    return DeadlineImportOut(created=created)
