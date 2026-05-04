from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    ChatMessage,
    ChatSession,
    ChatState,
    CalendarEventLink,
    Class,
    ClassNotes,
    Deadline,
    Document,
    DocumentChunk,
    GoogleIntegration,
    StudyPlan,
    UserSettings,
)

from app.services.chat.onboarding import initial_state, welcome_message


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


def update_class_timeline(
    *,
    db: Session,
    user_id: uuid.UUID,
    class_id: uuid.UUID,
    semester_start: str | None = None,
    semester_end: str | None = None,
    timezone: str | None = None,
    availability_json: dict[str, Any] | None = None,
) -> Class | None:
    clazz = get_class(db=db, user_id=user_id, class_id=class_id)
    if clazz is None:
        return None
    if semester_start is not None:
        clazz.semester_start = semester_start
    if semester_end is not None:
        clazz.semester_end = semester_end
    if timezone is not None:
        clazz.timezone = timezone
    if availability_json is not None:
        clazz.availability_json = availability_json
    db.add(clazz)
    db.commit()
    db.refresh(clazz)
    return clazz


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


def list_deadlines(
    *, db: Session, user_id: uuid.UUID, class_id: uuid.UUID
) -> list[Deadline]:
    stmt = (
        select(Deadline)
        .where(Deadline.class_id == class_id, Deadline.user_id == user_id)
        .order_by(desc(Deadline.created_at))
    )
    return list(db.execute(stmt).scalars().all())


def get_deadline(
    *,
    db: Session,
    user_id: uuid.UUID,
    class_id: uuid.UUID,
    deadline_id: uuid.UUID,
) -> Deadline | None:
    stmt = select(Deadline).where(
        Deadline.id == deadline_id,
        Deadline.class_id == class_id,
        Deadline.user_id == user_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def update_deadline_completion(
    *,
    db: Session,
    user_id: uuid.UUID,
    class_id: uuid.UUID,
    deadline_id: uuid.UUID,
    completed_at: Any | None,
) -> Deadline | None:
    d = get_deadline(db=db, user_id=user_id, class_id=class_id, deadline_id=deadline_id)
    if d is None:
        return None
    d.completed_at = completed_at
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def create_deadline(
    *,
    db: Session,
    user_id: uuid.UUID,
    class_id: uuid.UUID,
    title: str,
    due_text: str,
    due_at: Any | None = None,
) -> Deadline:
    deadline = Deadline(
        user_id=user_id,
        class_id=class_id,
        title=title,
        due_text=due_text,
        due_at=due_at,
    )
    db.add(deadline)
    db.commit()
    db.refresh(deadline)
    return deadline


def get_latest_study_plan(
    *, db: Session, user_id: uuid.UUID, class_id: uuid.UUID
) -> StudyPlan | None:
    stmt = (
        select(StudyPlan)
        .where(StudyPlan.class_id == class_id, StudyPlan.user_id == user_id)
        .order_by(desc(StudyPlan.created_at))
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_next_deadline(
    *, db: Session, user_id: uuid.UUID, class_id: uuid.UUID
) -> Deadline | None:
    """
    Return the next upcoming deadline for a class.

    Preference order:
    - earliest non-null due_at among incomplete deadlines
    - otherwise None (we do not try to sort due_text strings)
    """
    stmt = (
        select(Deadline)
        .where(
            Deadline.class_id == class_id,
            Deadline.user_id == user_id,
            Deadline.completed_at.is_(None),
            Deadline.due_at.is_not(None),
        )
        .order_by(Deadline.due_at.asc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def delete_deadline(
    *,
    db: Session,
    user_id: uuid.UUID,
    class_id: uuid.UUID,
    deadline_id: uuid.UUID,
) -> bool:
    stmt = select(Deadline).where(
        Deadline.id == deadline_id,
        Deadline.class_id == class_id,
        Deadline.user_id == user_id,
    )
    deadline = db.execute(stmt).scalar_one_or_none()
    if deadline is None:
        return False
    db.delete(deadline)
    db.commit()
    return True


def create_document(
    *,
    db: Session,
    user_id: uuid.UUID,
    class_id: uuid.UUID,
    filename: str,
    title: str | None,
    document_type: str,
    raw_text: str | None,
    metadata_json: dict[str, Any] | None = None,
) -> Document:
    doc = Document(
        user_id=user_id,
        class_id=class_id,
        filename=filename,
        title=title,
        document_type=document_type,
        raw_text=raw_text,
        metadata_json=metadata_json or {},
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def bulk_create_document_chunks(
    *,
    db: Session,
    chunks: list[DocumentChunk],
) -> int:
    db.add_all(chunks)
    db.commit()
    return len(chunks)


def get_active_chat_session(*, db: Session, user_id: uuid.UUID) -> ChatSession | None:
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == user_id, ChatSession.status == "active")
        .order_by(desc(ChatSession.created_at))
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def create_chat_session(*, db: Session, user_id: uuid.UUID) -> ChatSession:
    session = ChatSession(user_id=user_id, status="active")
    db.add(session)
    db.commit()
    db.refresh(session)
    # Create initial state row + first assistant message (materials-first onboarding).
    st = ChatState(session_id=session.id, user_id=user_id, state_json=initial_state())
    db.add(st)
    db.commit()
    add_chat_message(
        db=db,
        user_id=user_id,
        session_id=session.id,
        role="assistant",
        content=welcome_message(),
    )
    db.refresh(session)
    return session


def get_chat_session(
    *, db: Session, user_id: uuid.UUID, session_id: uuid.UUID
) -> ChatSession | None:
    stmt = select(ChatSession).where(
        ChatSession.id == session_id, ChatSession.user_id == user_id
    )
    return db.execute(stmt).scalar_one_or_none()


def list_chat_messages(
    *, db: Session, user_id: uuid.UUID, session_id: uuid.UUID
) -> list[ChatMessage]:
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at)
    )
    return list(db.execute(stmt).scalars().all())


def add_chat_message(
    *,
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    role: str,
    content: str,
) -> ChatMessage:
    msg = ChatMessage(
        user_id=user_id, session_id=session_id, role=role, content=content
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_chat_state(
    *, db: Session, user_id: uuid.UUID, session_id: uuid.UUID
) -> ChatState | None:
    stmt = select(ChatState).where(
        ChatState.session_id == session_id, ChatState.user_id == user_id
    )
    return db.execute(stmt).scalar_one_or_none()


def update_chat_state(
    *,
    db: Session,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    state_json: dict[str, Any],
) -> ChatState:
    st = get_chat_state(db=db, user_id=user_id, session_id=session_id)
    if st is None:
        st = ChatState(session_id=session_id, user_id=user_id, state_json=state_json)
        db.add(st)
        db.commit()
        db.refresh(st)
        return st
    st.state_json = state_json
    db.add(st)
    db.commit()
    db.refresh(st)
    return st


def upsert_google_integration(
    *,
    db: Session,
    user_id: uuid.UUID,
    refresh_token: str,
    access_token: str | None,
    token_expiry: Any | None,
    scopes: str,
) -> GoogleIntegration:
    stmt = select(GoogleIntegration).where(GoogleIntegration.user_id == user_id)
    existing = db.execute(stmt).scalar_one_or_none()
    if existing is None:
        existing = GoogleIntegration(
            user_id=user_id,
            refresh_token=refresh_token,
            access_token=access_token,
            token_expiry=token_expiry,
            scopes=scopes,
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    existing.refresh_token = refresh_token
    existing.access_token = access_token
    existing.token_expiry = token_expiry
    existing.scopes = scopes
    db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing


def get_google_integration(
    *, db: Session, user_id: uuid.UUID
) -> GoogleIntegration | None:
    stmt = select(GoogleIntegration).where(GoogleIntegration.user_id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def get_calendar_event_link(
    *,
    db: Session,
    user_id: uuid.UUID,
    kind: str,
    local_id: str,
) -> CalendarEventLink | None:
    stmt = select(CalendarEventLink).where(
        CalendarEventLink.user_id == user_id,
        CalendarEventLink.kind == kind,
        CalendarEventLink.local_id == local_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def upsert_calendar_event_link(
    *,
    db: Session,
    user_id: uuid.UUID,
    class_id: uuid.UUID,
    kind: str,
    local_id: str,
    google_calendar_id: str,
    google_event_id: str,
) -> CalendarEventLink:
    link = get_calendar_event_link(db=db, user_id=user_id, kind=kind, local_id=local_id)
    if link is None:
        link = CalendarEventLink(
            user_id=user_id,
            class_id=class_id,
            kind=kind,
            local_id=local_id,
            google_calendar_id=google_calendar_id,
            google_event_id=google_event_id,
        )
        db.add(link)
        db.commit()
        db.refresh(link)
        return link
    link.class_id = class_id
    link.google_calendar_id = google_calendar_id
    link.google_event_id = google_event_id
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def get_user_settings(*, db: Session, user_id: uuid.UUID) -> UserSettings | None:
    stmt = select(UserSettings).where(UserSettings.user_id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def upsert_user_settings(
    *,
    db: Session,
    user_id: uuid.UUID,
    notifications_enabled: bool | None = None,
    days_before_deadline: int | None = None,
    timezone: str | None = None,
) -> UserSettings:
    existing = get_user_settings(db=db, user_id=user_id)
    if existing is None:
        existing = UserSettings(
            user_id=user_id,
            notifications_enabled=(
                notifications_enabled if notifications_enabled is not None else True
            ),
            days_before_deadline=(
                days_before_deadline if days_before_deadline is not None else 3
            ),
            timezone=timezone,
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    if notifications_enabled is not None:
        existing.notifications_enabled = notifications_enabled
    if days_before_deadline is not None:
        existing.days_before_deadline = days_before_deadline
    if timezone is not None:
        existing.timezone = timezone
    db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing
