from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _hhmm_to_minutes(value: str) -> int:
    hh, mm = value.split(":")
    return int(hh) * 60 + int(mm)


class ClassMeetingPattern(BaseModel):
    """Recurring lecture pattern in the class timezone.

    weekdays uses Python's Monday=0 ... Sunday=6 convention so it lines up with
    `datetime.weekday()`.
    """

    weekdays: list[int] = Field(min_length=1, max_length=7)
    start_time: str = Field(min_length=5, max_length=5)
    end_time: str = Field(min_length=5, max_length=5)

    @field_validator("weekdays")
    @classmethod
    def _check_weekdays(cls, v: list[int]) -> list[int]:
        for day in v:
            if not 0 <= day <= 6:
                raise ValueError("weekdays must be integers in [0, 6]")
        if len(set(v)) != len(v):
            raise ValueError("weekdays must not contain duplicates")
        return sorted(v)

    @field_validator("start_time", "end_time")
    @classmethod
    def _check_hhmm(cls, v: str) -> str:
        if not _HHMM_RE.match(v):
            raise ValueError("time must be HH:MM in 24h format")
        return v

    @model_validator(mode="after")
    def _check_order(self) -> "ClassMeetingPattern":
        if _hhmm_to_minutes(self.start_time) >= _hhmm_to_minutes(self.end_time):
            raise ValueError("start_time must be earlier than end_time")
        return self


class ClassCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class GradeBookComponent(BaseModel):
    """One syllabus category (exam, homework bucket, final, …) with optional score."""

    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    weight_percent: float = Field(ge=0, le=100)
    score_percent: float | None = Field(default=None, ge=0, le=100)


class LetterGradeCutoff(BaseModel):
    letter: str = Field(min_length=1, max_length=4)
    min_percent: float = Field(ge=0, le=100)


class GradeBookState(BaseModel):
    """Weighted grade setup from the syllabus plus scores the student enters."""

    components: list[GradeBookComponent] = Field(default_factory=list, max_length=40)
    pass_percent: float = Field(default=60.0, ge=0, le=100)
    target_percent: float = Field(default=73.0, ge=0, le=100)
    letter_cutoffs: list[LetterGradeCutoff] = Field(
        default_factory=lambda: [
            LetterGradeCutoff(letter="A", min_percent=90),
            LetterGradeCutoff(letter="B", min_percent=80),
            LetterGradeCutoff(letter="C", min_percent=70),
            LetterGradeCutoff(letter="D", min_percent=60),
        ]
    )

    @model_validator(mode="after")
    def _weights_and_cutoffs(self) -> "GradeBookState":
        if self.components:
            total_w = sum(c.weight_percent for c in self.components)
            if abs(total_w - 100.0) > 0.02:
                raise ValueError("Component weights must sum to 100%")
        letters = [c.letter.upper() for c in self.letter_cutoffs]
        if len(letters) != len(set(letters)):
            raise ValueError("letter_cutoffs must not duplicate letters")
        return self


class ClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    semester_start: str | None = None
    semester_end: str | None = None
    timezone: str | None = None
    availability_json: dict[str, Any] | None = None
    meeting_pattern: ClassMeetingPattern | None = None
    grade_book: GradeBookState | None = None
    created_at: datetime

    @field_validator("grade_book", mode="before")
    @classmethod
    def _coerce_grade_book(cls, v: Any) -> Any:
        if v is None or isinstance(v, GradeBookState):
            return v
        if isinstance(v, dict):
            return GradeBookState.model_validate(v)
        return v


class ClassTimelineUpdate(BaseModel):
    semester_start: str | None = Field(default=None, max_length=40)
    semester_end: str | None = Field(default=None, max_length=40)
    timezone: str | None = Field(default=None, max_length=60)
    availability: list["StudyAvailabilityBlock"] | None = None
    meeting_pattern: ClassMeetingPattern | None = None


class ClassSummaryOut(BaseModel):
    clazz: ClassOut
    deadline_count: int
    next_deadline_id: uuid.UUID | None = None
    next_deadline_title: str | None = None
    next_deadline_due_at: datetime | None = None
    latest_study_plan_id: uuid.UUID | None = None
    latest_study_plan_created_at: datetime | None = None
    # True when at least one RAG document was indexed with document_type "syllabus".
    has_indexed_syllabus: bool = False


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


class StudyPlanUpdate(BaseModel):
    completed_tasks: list[str]


class StudyPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    class_id: uuid.UUID
    user_id: uuid.UUID
    source_notes_id: uuid.UUID | None
    plan_json: dict[str, Any]
    model: str
    created_at: datetime
    # Populated only by the create endpoint when the user has opted into
    # auto-scheduling AND Google Calendar is connected: one entry per plan
    # day that successfully landed on the GradePilot calendar. Other
    # endpoints (GET /latest, PATCH /progress) leave this as an empty list.
    scheduled_plan_sessions: list[dict[str, Any]] = []


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
    # Which saved notes / lecture this question is grounded in (e.g. "Lecture 2").
    source_label: str = Field(default="Class notes", min_length=1)


class PracticeQuestionsAI(BaseModel):
    questions: list[PracticeQuestion]


class PracticeGenerateRequest(BaseModel):
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


class PreferredStudyWindow(BaseModel):
    """A daily time window (user local time) where study sessions may land."""

    start: str = Field(min_length=5, max_length=5)
    end: str = Field(min_length=5, max_length=5)

    @field_validator("start", "end")
    @classmethod
    def _check_hhmm(cls, v: str) -> str:
        if not _HHMM_RE.match(v):
            raise ValueError("time must be HH:MM in 24h format")
        return v

    @model_validator(mode="after")
    def _check_order(self) -> "PreferredStudyWindow":
        if _hhmm_to_minutes(self.start) >= _hhmm_to_minutes(self.end):
            raise ValueError("start must be earlier than end")
        return self


class UserSettingsOut(BaseModel):
    notificationsEnabled: bool
    daysBeforeDeadline: int
    googleConnected: bool
    timezone: str | None = None
    preferredStudyWindows: list[PreferredStudyWindow] = Field(default_factory=list)
    autoScheduleSessions: bool = False


class UserSettingsUpdate(BaseModel):
    notificationsEnabled: bool | None = None
    daysBeforeDeadline: int | None = Field(default=None, ge=1, le=14)
    timezone: str | None = Field(default=None, max_length=60)
    preferredStudyWindows: list[PreferredStudyWindow] | None = Field(
        default=None, max_length=4
    )
    autoScheduleSessions: bool | None = None
