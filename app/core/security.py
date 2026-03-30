from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, cast

import httpx
from jose import jwt
from jose.exceptions import JWTError

from app.core.config import get_settings

logger = logging.getLogger("gradepilot.auth")


@dataclass(frozen=True)
class JWKSCache:
    jwks: dict[str, Any]
    expires_at: float


_jwks_cache: JWKSCache | None = None


def _get_jwks(*, now: float | None = None) -> dict[str, Any]:
    global _jwks_cache
    settings = get_settings()
    now_ts = time.time() if now is None else now

    if _jwks_cache is not None and _jwks_cache.expires_at > now_ts:
        return _jwks_cache.jwks

    with httpx.Client(timeout=5.0) as client:
        resp = client.get(settings.supabase_jwks_url)
        resp.raise_for_status()
        jwks = cast(dict[str, Any], resp.json())

    # Cache for 1 hour (Supabase rotates keys infrequently; this avoids per-request fetches)
    _jwks_cache = JWKSCache(jwks=jwks, expires_at=now_ts + 3600.0)
    return jwks


def verify_supabase_jwt(token: str) -> dict[str, Any]:
    """
    Verify a Supabase access token (JWT).

    Supabase commonly signs access tokens with HS256 (project JWT secret).
    Some setups use RS256 + JWKS. We support both based on JWT header alg.

    Returns decoded claims. Raises ValueError on invalid tokens.
    """
    settings = get_settings()
    try:
        header = cast(dict[str, Any], jwt.get_unverified_header(token))
        alg = header.get("alg")
        unverified = cast(dict[str, Any], jwt.get_unverified_claims(token))
        logger.info(
            "jwt_received alg=%s aud=%s iss=%s exp=%s sub_present=%s",
            alg,
            unverified.get("aud"),
            unverified.get("iss"),
            unverified.get("exp"),
            isinstance(unverified.get("sub"), str),
        )

        if alg in ("RS256", "ES256"):
            jwks = _get_jwks()
            claims = jwt.decode(
                token,
                jwks,
                algorithms=["RS256", "ES256"],
                audience=settings.supabase_jwt_audience,
                issuer=settings.supabase_jwt_issuer,
                options={"verify_aud": True, "verify_iss": True},
            )
        elif alg == "HS256":
            if not settings.supabase_jwt_secret:
                logger.warning("missing SUPABASE_JWT_SECRET for HS256 verification")
                raise ValueError(
                    "Server misconfigured: set SUPABASE_JWT_SECRET to verify Supabase tokens"
                )
            claims = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience=settings.supabase_jwt_audience,
                issuer=settings.supabase_jwt_issuer,
                options={"verify_aud": True, "verify_iss": True},
            )
        else:
            logger.warning("unsupported jwt alg=%s", alg)
            raise ValueError("Unsupported token algorithm")

        return cast(dict[str, Any], claims)
    except JWTError as e:
        logger.info("jwt_invalid reason=%s", e.__class__.__name__)
        raise ValueError("Invalid or expired token") from e
