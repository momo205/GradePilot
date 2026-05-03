from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import crud
from app.db.session import get_db
from app.deps.auth import CurrentUser, get_current_user
from app.schemas import UserSettingsOut, UserSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def _user_uuid(user: CurrentUser) -> uuid.UUID:
    try:
        return uuid.UUID(user.user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user id")


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
        )

    return UserSettingsOut(
        notificationsEnabled=bool(st.notifications_enabled),
        daysBeforeDeadline=int(st.days_before_deadline),
        googleConnected=google_connected,
        timezone=st.timezone,
    )


@router.put("", response_model=UserSettingsOut)
def update_settings_endpoint(
    payload: UserSettingsUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSettingsOut:
    user_id = _user_uuid(user)
    st = crud.upsert_user_settings(
        db=db,
        user_id=user_id,
        notifications_enabled=payload.notificationsEnabled,
        days_before_deadline=payload.daysBeforeDeadline,
        timezone=payload.timezone,
    )
    google_connected = crud.get_google_integration(db=db, user_id=user_id) is not None
    return UserSettingsOut(
        notificationsEnabled=bool(st.notifications_enabled),
        daysBeforeDeadline=int(st.days_before_deadline),
        googleConnected=google_connected,
        timezone=st.timezone,
    )
