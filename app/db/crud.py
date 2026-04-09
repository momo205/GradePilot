from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import Class, ClassNotes, StudyPlan


def list_classes(*, db: Session, user_id: uuid.UUID) -> list[Class]:
    stmt = (
        select(Class).where(Class.user_id == user_id).order_by(desc(Class.created_at))
    )
    return list(db.execute(stmt).scalars().all())


def create_class(*, db: Session, user_id: uuid.UUID, title: str) -> Class:
    clazz = Class(user_id=user_id, title=title)
    db.add(clazz)
    db.commit()
    db.refresh(clazz)
    return clazz


def get_class(*, db: Session, user_id: uuid.UUID, class_id: uuid.UUID) -> Class | None:
    stmt = select(Class).where(Class.id == class_id, Class.user_id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def create_notes(
    *, db: Session, user_id: uuid.UUID, class_id: uuid.UUID, notes_text: str
) -> ClassNotes:
    notes = ClassNotes(user_id=user_id, class_id=class_id, notes_text=notes_text)
    db.add(notes)
    db.commit()
    db.refresh(notes)
    return notes


def get_notes(
    *, db: Session, user_id: uuid.UUID, notes_id: uuid.UUID
) -> ClassNotes | None:
    stmt = select(ClassNotes).where(
        ClassNotes.id == notes_id, ClassNotes.user_id == user_id
    )
    return db.execute(stmt).scalar_one_or_none()


def get_latest_notes(
    *, db: Session, user_id: uuid.UUID, class_id: uuid.UUID
) -> ClassNotes | None:
    stmt = (
        select(ClassNotes)
        .where(ClassNotes.class_id == class_id, ClassNotes.user_id == user_id)
        .order_by(desc(ClassNotes.created_at))
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def list_notes(
    *, db: Session, user_id: uuid.UUID, class_id: uuid.UUID
) -> list[ClassNotes]:
    stmt = (
        select(ClassNotes)
        .where(ClassNotes.class_id == class_id, ClassNotes.user_id == user_id)
        .order_by(desc(ClassNotes.created_at))
    )
    return list(db.execute(stmt).scalars().all())


def create_study_plan(
    *,
    db: Session,
    user_id: uuid.UUID,
    class_id: uuid.UUID,
    source_notes_id: uuid.UUID | None,
    plan_json: dict[str, Any],
    model: str,
) -> StudyPlan:
    plan = StudyPlan(
        user_id=user_id,
        class_id=class_id,
        source_notes_id=source_notes_id,
        plan_json=plan_json,
        model=model,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan
