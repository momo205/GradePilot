from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def get_engine() -> Engine:
    settings = get_settings()
    url = settings.database_url
    # Supabase UI often provides `postgresql://...` which defaults to psycopg2 in SQLAlchemy.
    # This project uses psycopg v3, so normalize the scheme.
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(url, pool_pre_ping=True)


_ENGINE: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _get_sessionmaker() -> sessionmaker[Session]:
    global _ENGINE, _SessionLocal
    if _SessionLocal is None:
        _ENGINE = get_engine()
        from app.db.models import Base

        Base.metadata.create_all(bind=_ENGINE)
        _SessionLocal = sessionmaker(bind=_ENGINE, autocommit=False, autoflush=False)
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    SessionLocal = _get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
