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
    created_at: datetime


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
