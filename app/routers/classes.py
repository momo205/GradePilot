from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import crud
from app.db.session import get_db
from app.deps.auth import CurrentUser, get_current_user
from app.schemas import (
    ClassCreate,
    ClassOut,
    NotesCreate,
    NotesOut,
    StudyPlanCreate,
    StudyPlanOut,
)
from app.services.study_plan import StudyPlanGenerationError, generate_study_plan

router = APIRouter(prefix="/classes", tags=["classes"])


def _user_uuid(user: CurrentUser) -> uuid.UUID:
    try:
        return uuid.UUID(user.user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user id")


@router.post("", response_model=ClassOut)
def create_class(
    payload: ClassCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClassOut:
    clazz = crud.create_class(db=db, user_id=_user_uuid(user), title=payload.title)
    return ClassOut.model_validate(clazz)


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
