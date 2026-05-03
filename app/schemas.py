from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ClassCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    semester_start: str | None = None
    semester_end: str | None = None
    timezone: str | None = None
    availability_json: dict[str, Any] | None = None
    created_at: datetime


class ClassTimelineUpdate(BaseModel):
    semester_start: str | None = Field(default=None, max_length=40)
    semester_end: str | None = Field(default=None, max_length=40)
    timezone: str | None = Field(default=None, max_length=60)
    availability: list["StudyAvailabilityBlock"] | None = None


class ClassSummaryOut(BaseModel):
    clazz: ClassOut
    deadline_count: int
    next_deadline_id: uuid.UUID | None = None
    next_deadline_title: str | None = None
    next_deadline_due_at: datetime | None = None
    latest_study_plan_id: uuid.UUID | None = None
    latest_study_plan_created_at: datetime | None = None


class NotesCreate(BaseModel):
    notes_text: str = Field(min_length=1)


class NotesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    class_id: uuid.UUID
    user_id: uuid.UUID
    notes_text: str
    created_at: datetime


class StudyPlanCreate(BaseModel):
    notes_id: uuid.UUID | None = None


class StudyPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    class_id: uuid.UUID
    user_id: uuid.UUID
    source_notes_id: uuid.UUID | None
    plan_json: dict[str, Any]
    model: str
    created_at: datetime


class StudyPlanAIItem(BaseModel):
    day: str
    tasks: list[str]


class StudyPlanAI(BaseModel):
    title: str
    goals: list[str]
    schedule: list[StudyPlanAIItem]


class PracticeQuestion(BaseModel):
    q: str
    a: str


class PracticeQuestionsAI(BaseModel):
    questions: list[PracticeQuestion]


class PracticeGenerateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    count: int = Field(default=5, ge=1, le=10)
    difficulty: Literal["Easy", "Medium", "Hard"] = "Medium"


class PracticeGenerateOut(BaseModel):
    questions: list[PracticeQuestion]


class SummariseRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    raw_text: str = Field(min_length=1)


class SummariseOut(BaseModel):
    title: str
    summary: str
    key_topics: list[str]
    important_dates: list[str]
    extracted_notes: str


class ExtractPdfOut(BaseModel):
    filename: str
    raw_text: str


class DeadlineCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due: str = Field(min_length=1, max_length=500)


class DeadlineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    class_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    due_text: str
    due_at: datetime | None
    completed_at: datetime | None = None
    created_at: datetime


class DeadlineUpdate(BaseModel):
    completed: bool | None = None


class MaterialIngestOut(BaseModel):
    document_id: uuid.UUID
    chunks_created: int


class ClassAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=6, ge=1, le=20)
    document_type: str | None = Field(default=None, max_length=50)


class ClassAskSource(BaseModel):
    document_id: str
    filename: str
    document_type: str
    chunk_index: int
    snippet: str


class ClassAskOut(BaseModel):
    answer: str
    sources: list[ClassAskSource]


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    status: str
    created_at: datetime


class ChatMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class ChatStateOut(BaseModel):
    state: dict[str, Any]


class ChatToolAction(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ChatReplyOut(BaseModel):
    session: ChatSessionOut
    messages: list[ChatMessageOut]
    state: dict[str, Any]
    tool_actions: list[ChatToolAction] = Field(default_factory=list)
    complete: bool = False
    class_id: uuid.UUID | None = None
    next_url: str | None = None


class DeadlineImportOut(BaseModel):
    created: int


class StudyAvailabilityBlock(BaseModel):
    day: str = Field(min_length=1, max_length=20)  # e.g. Mon, Tuesday
    start_time: str = Field(min_length=1, max_length=10)  # e.g. 17:00
    end_time: str = Field(min_length=1, max_length=10)  # e.g. 21:00


class StudyPlanSemesterTaskAI(BaseModel):
    title: str
    estimated_hours: float = Field(ge=0.5, le=8.0)
    deadline_id: str | None = None


class StudyPlanSemesterWeekAI(BaseModel):
    week: int = Field(ge=1)
    start: str
    end: str
    goals: list[str]
    tasks: list[StudyPlanSemesterTaskAI]


class StudyPlanSemesterAI(BaseModel):
    title: str
    timezone: str
    semester_start: str
    semester_end: str
    weeks: list[StudyPlanSemesterWeekAI]


class StudyPlanSemesterCreate(BaseModel):
    semester_start: str = Field(min_length=1, max_length=40)
    semester_end: str = Field(min_length=1, max_length=40)
    timezone: str = Field(min_length=1, max_length=60)
    availability: list[StudyAvailabilityBlock] | None = None


class UserSettingsOut(BaseModel):
    notificationsEnabled: bool
    daysBeforeDeadline: int
    googleConnected: bool
    timezone: str | None = None


class UserSettingsUpdate(BaseModel):
    notificationsEnabled: bool | None = None
    daysBeforeDeadline: int | None = Field(default=None, ge=1, le=14)
    timezone: str | None = Field(default=None, max_length=60)
