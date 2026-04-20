from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime, timedelta
import uuid

router = APIRouter(prefix="/calendar", tags=["calendar"])

class EventOut(BaseModel):
    id: str | int
    title: str
    start_datetime: str
    end_datetime: str

# Use the same data from the old MOCK_EVENTS, but served from backend now.
now = datetime.now()

MOCK_BACKEND_EVENTS = [
    {
        "id": 1,
        "title": "Data Structures Midterm",
        "start_datetime": datetime(now.year, now.month, 15, 10, 0).isoformat(),
        "end_datetime": datetime(now.year, now.month, 15, 12, 0).isoformat(),
    },
    {
        "id": 2,
        "title": "Study: Binary Trees",
        "start_datetime": datetime(now.year, now.month, 12, 14, 0).isoformat(),
        "end_datetime": datetime(now.year, now.month, 12, 16, 0).isoformat(),
    },
    {
        "id": 3,
        "title": "Assignment 3 Due",
        "start_datetime": datetime(now.year, now.month, 18, 23, 59).isoformat(),
        "end_datetime": datetime(now.year, now.month, 18, 23, 59).isoformat(),
    },
    {
        "id": 4,
        "title": "Study: Graph Algorithms",
        "start_datetime": datetime(now.year, now.month, 20, 18, 0).isoformat(),
        "end_datetime": datetime(now.year, now.month, 20, 20, 0).isoformat(),
    },
    {
        "id": 5,
        "title": "Review Notes",
        "start_datetime": datetime(now.year, now.month, now.day, 16, 0).isoformat(),
        "end_datetime": datetime(now.year, now.month, now.day, 18, 0).isoformat(),
    },
]

@router.get("/events", response_model=list[EventOut])
def get_events():
    return MOCK_BACKEND_EVENTS

@router.post("/sync")
def sync_events():
    return {"status": "synced"}

