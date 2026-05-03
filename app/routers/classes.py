from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

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
    NotesCreate,
    NotesOut,
    PracticeGenerateOut,
    PracticeGenerateRequest,
    StudyPlanCreate,
    StudyPlanOut,
    StudyPlanSemesterCreate,
)
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


def _user_uuid(user: CurrentUser) -> uuid.UUID:
    try:
        return uuid.UUID(user.user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user id")


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

    return ClassSummaryOut(
        clazz=ClassOut.model_validate(clazz),
        deadline_count=len(deadlines),
        next_deadline_id=(next_deadline.id if next_deadline else None),
        next_deadline_title=(next_deadline.title if next_deadline else None),
        next_deadline_due_at=(next_deadline.due_at if next_deadline else None),
        latest_study_plan_id=(latest_plan.id if latest_plan else None),
        latest_study_plan_created_at=(latest_plan.created_at if latest_plan else None),
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
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Class not found")
    return ClassOut.model_validate(updated)


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
def add_notes(
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
    try:
        questions = generate_practice_questions(
            class_title=clazz.title,
            topic=payload.topic,
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

    try:
        plan_json, model_name = generate_study_plan(
            class_title=clazz.title, notes_text=notes.notes_text
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
    return StudyPlanOut.model_validate(plan)


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
def create_deadline_endpoint(
    class_id: uuid.UUID,
    payload: DeadlineCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeadlineOut:
    user_id = _user_uuid(user)
    clazz = crud.get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        raise HTTPException(status_code=404, detail="Class not found")
    created = crud.create_deadline(
        db=db,
        user_id=user_id,
        class_id=class_id,
        title=payload.title,
        due_text=payload.due,
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
        raise HTTPException(status_code=502, detail=str(e))

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

    return DeadlineImportOut(created=created)
