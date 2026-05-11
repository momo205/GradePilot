from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # dotenv is optional; production should provide real environment variables
    pass


def _get_env(name: str, *, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_jwt_issuer: str
    supabase_jwks_url: str
    supabase_jwt_audience: str
    supabase_jwt_secret: str | None

    database_url: str
    google_api_key: str | None
    google_model: str
    google_embedding_model: str

    google_oauth_client_id: str | None
    google_oauth_client_secret: str | None
    google_oauth_redirect_uri: str | None


def get_settings() -> Settings:
    supabase_url = _get_env("SUPABASE_URL")
    issuer = os.getenv("SUPABASE_JWT_ISSUER") or f"{supabase_url.rstrip('/')}/auth/v1"
    jwks_url = os.getenv("SUPABASE_JWKS_URL") or (
        f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    )

    database_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL") or ""
    if database_url == "":
        raise RuntimeError(
            "Missing DATABASE_URL (or SUPABASE_DATABASE_URL) for DB connection"
        )

    return Settings(
        supabase_url=supabase_url,
        supabase_jwt_issuer=issuer,
        supabase_jwks_url=jwks_url,
        supabase_jwt_audience=os.getenv("SUPABASE_JWT_AUD", "authenticated"),
        supabase_jwt_secret=os.getenv("SUPABASE_JWT_SECRET"),
        database_url=database_url,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        google_model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
        # Used by the google-genai SDK (Gemini Developer API). Can be overridden via env.
        google_embedding_model=os.getenv(
            "GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001"
        ),
        google_oauth_client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
        google_oauth_client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
        google_oauth_redirect_uri=os.getenv("GOOGLE_OAUTH_REDIRECT_URI"),
    )
