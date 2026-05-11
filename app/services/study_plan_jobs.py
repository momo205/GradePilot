from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session, sessionmaker

from app.db import crud
from app.db.session import get_engine
from app.routers.classes import _compute_plan_horizon
from app.services.study_plan import (
    StudyPlanGenerationError,
    StudyPlanRateLimitError,
    generate_study_plan,
)
from app.services.scheduling.plan_sessions import schedule_plan_day_sessions

logger = logging.getLogger("gradepilot.study_plan_jobs")


def _make_session() -> Session:
    engine = get_engine()
    SessionLocal: sessionmaker[Session] = sessionmaker(
        bind=engine, autocommit=False, autoflush=False
    )
    return SessionLocal()


def _set_job(
    *,
    db: Session,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    status: str | None = None,
    phase: str | None = None,
    progress: int | None = None,
    message: str | None = None,
    error: str | None = None,
    result_plan_id: uuid.UUID | None = None,
) -> None:
    crud.update_study_plan_job(
        db=db,
        user_id=user_id,
        job_id=job_id,
        status=status,
        phase=phase,
        progress=progress,
        message=message,
        error=error,
        result_plan_id=result_plan_id,
    )


def run_study_plan_job(*, user_id: uuid.UUID, job_id: uuid.UUID) -> None:
    """Execute a study-plan job and persist status updates to the DB.

    This is designed to be launched from FastAPI BackgroundTasks.
    """
    db = _make_session()
    try:
        job = crud.get_study_plan_job(db=db, user_id=user_id, job_id=job_id)
        if job is None:
            return

        _set_job(
            db=db,
            user_id=user_id,
            job_id=job_id,
            status="running",
            phase="validating",
            progress=5,
            message="Validating inputs…",
            error=None,
        )

        clazz = crud.get_class(db=db, user_id=user_id, class_id=job.class_id)
        if clazz is None:
            _set_job(
                db=db,
                user_id=user_id,
                job_id=job_id,
                status="failed",
                phase="failed",
                progress=100,
                error="Class not found",
                message=None,
            )
            return

        if job.notes_id is not None:
            notes = crud.get_notes(db=db, user_id=user_id, notes_id=job.notes_id)
            if notes is None or notes.class_id != job.class_id:
                _set_job(
                    db=db,
                    user_id=user_id,
                    job_id=job_id,
                    status="failed",
                    phase="failed",
                    progress=100,
                    error="Notes not found",
                    message=None,
                )
                return
        else:
            notes = crud.get_latest_notes(db=db, user_id=user_id, class_id=job.class_id)
            if notes is None:
                _set_job(
                    db=db,
                    user_id=user_id,
                    job_id=job_id,
                    status="failed",
                    phase="failed",
                    progress=100,
                    error="No notes available for class",
                    message=None,
                )
                return

        horizon_days, horizon_reason = _compute_plan_horizon(
            db=db, user_id=user_id, class_id=job.class_id, clazz=clazz
        )

        _set_job(
            db=db,
            user_id=user_id,
            job_id=job_id,
            phase="generating",
            progress=20,
            message="Generating study plan…",
        )

        try:
            plan_json, model_name = generate_study_plan(
                class_title=clazz.title,
                notes_text=notes.notes_text,
                horizon_days=horizon_days,
                horizon_reason=horizon_reason,
            )
        except StudyPlanRateLimitError as e:
            _set_job(
                db=db,
                user_id=user_id,
                job_id=job_id,
                status="failed",
                phase="failed",
                progress=100,
                error=str(e),
                message=None,
            )
            return
        except StudyPlanGenerationError as e:
            _set_job(
                db=db,
                user_id=user_id,
                job_id=job_id,
                status="failed",
                phase="failed",
                progress=100,
                error=str(e),
                message=None,
            )
            return

        _set_job(
            db=db,
            user_id=user_id,
            job_id=job_id,
            phase="saving",
            progress=75,
            message="Saving plan…",
        )

        plan = crud.create_study_plan(
            db=db,
            user_id=user_id,
            class_id=job.class_id,
            source_notes_id=notes.id,
            plan_json=plan_json,
            model=model_name,
        )

        # Optional: best-effort day scheduling. We keep it inside the job (not the
        # immediate API response), but still never fail the job if scheduling fails.
        _set_job(
            db=db,
            user_id=user_id,
            job_id=job_id,
            phase="scheduling_calendar",
            progress=85,
            message="Scheduling calendar blocks…",
            result_plan_id=plan.id,
        )
        try:
            user_settings = crud.get_user_settings(db=db, user_id=user_id)
            if (
                user_settings is not None
                and bool(user_settings.auto_schedule_sessions)
                and crud.get_google_integration(db=db, user_id=user_id) is not None
            ):
                schedule_plan_day_sessions(
                    db=db,
                    user_id=user_id,
                    class_id=job.class_id,
                    plan_id=plan.id,
                    plan_json=plan_json,
                    class_title=clazz.title,
                    user_timezone=(user_settings.timezone or clazz.timezone or "UTC"),
                    preferred_windows=list(user_settings.preferred_study_windows or []),
                    now_utc=datetime.now(timezone.utc),
                )
        except Exception:
            logger.exception(
                "study_plan_job_calendar_schedule_failed job_id=%s", job_id
            )

        _set_job(
            db=db,
            user_id=user_id,
            job_id=job_id,
            status="succeeded",
            phase="done",
            progress=100,
            message="Done.",
            result_plan_id=plan.id,
            error=None,
        )
    except Exception as e:  # noqa: BLE001
        # Best-effort attempt to mark job failed (if DB is usable).
        try:
            _set_job(
                db=db,
                user_id=user_id,
                job_id=job_id,
                status="failed",
                phase="failed",
                progress=100,
                error=f"Unexpected error: {e.__class__.__name__}",
                message=None,
            )
        except Exception:
            pass
        logger.exception("study_plan_job_failed job_id=%s", job_id)
    finally:
        db.close()
