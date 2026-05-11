from __future__ import annotations

from app.services.chat.onboarding_gate import run_onboarding_gate


def test_phase3_valid_timeline_advances_to_phase4_and_generates() -> None:
    st = {"phase": 3, "class_id": "12345678-1234-5678-1234-567812345678"}
    msg = '{"timezone":"America/New_York","semester_start":"2026-09-01","semester_end":"2026-12-15"}'
    assistant, next_st, actions = run_onboarding_gate(state=st, user_message=msg)
    assert next_st["phase"] == 4
    assert any(a.get("type") == "set_class_timeline" for a in actions)
    assert any(a.get("type") == "generate_semester_plan" for a in actions)
    assert "generat" in assistant.lower() or "saved" in assistant.lower()


def test_phase2_does_not_accept_timeline_json() -> None:
    st = {"phase": 2, "class_id": "12345678-1234-5678-1234-567812345678"}
    msg = '{"timezone":"America/New_York","semester_start":"2026-09-01","semester_end":"2026-12-15"}'
    assistant, next_st, actions = run_onboarding_gate(state=st, user_message=msg)
    assert next_st["phase"] == 2
    assert actions == []
    assert "upload" in assistant.lower()
