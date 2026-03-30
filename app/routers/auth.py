from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps.auth import CurrentUser, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user)) -> dict[str, object]:
    return {"user_id": user.user_id, "claims": user.claims}
