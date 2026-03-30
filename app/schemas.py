from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

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
