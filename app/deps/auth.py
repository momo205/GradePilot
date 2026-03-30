from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_supabase_jwt
import logging

_bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger("gradepilot.auth")


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    claims: dict[str, Any]


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing bearer token")

    try:
        claims = verify_supabase_jwt(credentials.credentials)
    except ValueError as e:
        logger.info("auth_failed detail=%s", str(e))
        raise HTTPException(
            status_code=401, detail=str(e) or "Invalid or expired token"
        )

    sub = claims.get("sub")
    if not isinstance(sub, str) or sub == "":
        raise HTTPException(status_code=401, detail="Invalid token subject")

    return CurrentUser(user_id=sub, claims=claims)
