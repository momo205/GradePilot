from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import crud
from app.db.models import UserSettings
from app.db.session import get_db
from app.deps.auth import CurrentUser, get_current_user
from app.schemas import PreferredStudyWindow, UserSettingsOut, UserSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def _user_uuid(user: CurrentUser) -> uuid.UUID:
    try:
        return uuid.UUID(user.user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user id")


def _windows_from_db(st: UserSettings) -> list[PreferredStudyWindow]:
    raw = st.preferred_study_windows or []
    out: list[PreferredStudyWindow] = []
    for w in raw:
        if not isinstance(w, dict):
            continue
        start = w.get("start")
        end = w.get("end")
        if isinstance(start, str) and isinstance(end, str):
            # Drop rows that fail validation rather than 500 the whole request;
            # legacy rows can predate the validator.
            try:
                out.append(PreferredStudyWindow(start=start, end=end))
            except ValueError:
                continue
    return out


@router.get("", response_model=UserSettingsOut)
def get_settings_endpoint(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSettingsOut:
    user_id = _user_uuid(user)
    st = crud.get_user_settings(db=db, user_id=user_id)
    google_connected = crud.get_google_integration(db=db, user_id=user_id) is not None

    if st is None:
        # Default row is not created until first update; return defaults.
        return UserSettingsOut(
            notificationsEnabled=True,
            daysBeforeDeadline=3,
            googleConnected=google_connected,
            timezone=None,
            preferredStudyWindows=[],
            autoScheduleSessions=False,
        )

    return UserSettingsOut(
        notificationsEnabled=bool(st.notifications_enabled),
        daysBeforeDeadline=int(st.days_before_deadline),
        googleConnected=google_connected,
        timezone=st.timezone,
        preferredStudyWindows=_windows_from_db(st),
        autoScheduleSessions=bool(st.auto_schedule_sessions),
    )


@router.put("", response_model=UserSettingsOut)
def update_settings_endpoint(
    payload: UserSettingsUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSettingsOut:
    user_id = _user_uuid(user)
    windows_payload: list[dict[str, str]] | None = (
        [w.model_dump() for w in payload.preferredStudyWindows]
        if payload.preferredStudyWindows is not None
        else None
    )
    st = crud.upsert_user_settings(
        db=db,
        user_id=user_id,
        notifications_enabled=payload.notificationsEnabled,
        days_before_deadline=payload.daysBeforeDeadline,
        timezone=payload.timezone,
        preferred_study_windows=windows_payload,
        auto_schedule_sessions=payload.autoScheduleSessions,
    )
    google_connected = crud.get_google_integration(db=db, user_id=user_id) is not None
    return UserSettingsOut(
        notificationsEnabled=bool(st.notifications_enabled),
        daysBeforeDeadline=int(st.days_before_deadline),
        googleConnected=google_connected,
        timezone=st.timezone,
        preferredStudyWindows=_windows_from_db(st),
        autoScheduleSessions=bool(st.auto_schedule_sessions),
    )
