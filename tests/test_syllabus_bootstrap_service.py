from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest


def test_syllabus_bootstrap_helpers() -> None:
    from app.services.syllabus import onboarding_bootstrap as svc

    assert svc._coerce_semester_term(None) is None
    assert svc._coerce_semester_term("  FALL ") == "fall"
    assert svc._coerce_semester_term("Autumn") == "fall"
    assert svc._coerce_semester_term("spring") == "spring"
    assert svc._coerce_semester_term("winter") is None

    assert svc._infer_term_from_start_date(None) is None
    assert svc._infer_term_from_start_date("not-a-date") is None
    assert svc._infer_term_from_start_date("2026-09-01") == "fall"
    assert svc._infer_term_from_start_date("2026-02-01") == "spring"
    assert svc._infer_term_from_start_date("2026-07-01") is None

    tz, start, end = svc._coerce_timeline_dates(
        "  America/New_York  ", "2026-09-01", "bad"
    )
    assert tz == "America/New_York"
    assert start == "2026-09-01"
    assert end is None


def test_run_onboarding_syllabus_bootstrap_empty_pdf_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.syllabus import onboarding_bootstrap as svc
    from app.services.deadlines.extract import DeadlineExtractError

    monkeypatch.setattr(svc, "extract_text_from_pdf_bytes", lambda _b: "   ")

    with pytest.raises(DeadlineExtractError) as e:
        svc.run_onboarding_syllabus_bootstrap(
            db=MagicMock(),
            user_id=uuid.uuid4(),
            class_id=uuid.uuid4(),
            filename="syllabus.pdf",
            pdf_bytes=b"%PDF-1.4",
        )
    assert "No extractable text" in str(e.value)


def test_run_onboarding_syllabus_bootstrap_happy_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.syllabus import onboarding_bootstrap as svc

    monkeypatch.setattr(
        svc,
        "extract_text_from_pdf_bytes",
        lambda _b: "Course: CS101\nFall 2026\nHomework due weekly.",
    )

    parsed = svc.SyllabusBootstrapExtractAI.model_validate(
        {
            "deadlines": [
                {
                    "title": "HW1",
                    "due_text": "Oct 5 11:59pm",
                    "due_at": "2026-10-05T23:59:00-04:00",
                    "confidence": 0.9,
                    "source_quote": "HW1 due Oct 5",
                },
                {
                    "title": "Midterm",
                    "due_text": "Oct 20",
                    "due_at": None,
                    "confidence": 0.8,
                    "source_quote": "Midterm Oct 20",
                },
            ],
            "course_summary": "This course introduces core CS concepts.",
            "semester_timezone": " America/New_York ",
            "semester_start": "2026-09-01",
            "semester_end": "2026-12-15",
            "semester_term": None,
        }
    )
    monkeypatch.setattr(
        svc,
        "extract_syllabus_bootstrap_ai",
        lambda **_kw: parsed,
    )

    ingest_calls: list[tuple[str, str]] = []

    def _fake_ingest_raw_text(
        *,
        document_type: str,
        filename: str,
        raw_text: str,
        **_kw: object,
    ) -> MagicMock:
        ingest_calls.append((document_type, filename))
        # mimic ingest result
        return MagicMock(chunks_created=3 if document_type == "syllabus" else 1)

    monkeypatch.setattr(svc, "ingest_raw_text", _fake_ingest_raw_text)
    monkeypatch.setattr(svc, "_parse_due_at", lambda v: v)

    created_deadlines: list[dict[str, object]] = []

    def _fake_create_deadline(**kwargs: object) -> MagicMock:
        created_deadlines.append(kwargs)
        return MagicMock()

    from app.db import crud as db_crud

    monkeypatch.setattr(db_crud, "create_deadline", _fake_create_deadline)

    out = svc.run_onboarding_syllabus_bootstrap(
        db=MagicMock(),
        user_id=uuid.uuid4(),
        class_id=uuid.uuid4(),
        filename="syllabus.pdf",
        pdf_bytes=b"%PDF-1.4",
    )

    assert out.deadlines_created == 2
    assert out.syllabus_chunks == 3
    assert out.course_summary_chunks == 1
    assert out.suggested_timezone == "America/New_York"
    assert out.suggested_semester_start == "2026-09-01"
    assert out.suggested_semester_end == "2026-12-15"
    assert out.suggested_semester_term == "fall"

    assert ingest_calls[0][0] == "syllabus"
    assert any(dt == "course_summary" for dt, _fn in ingest_calls)
    assert len(created_deadlines) == 2
