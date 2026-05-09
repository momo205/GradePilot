from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.chat.onboarding_gate import (
    WELCOME_MESSAGE,
    initial_state as _initial_state,
    run_onboarding_gate,
)


@dataclass(frozen=True)
class OnboardingResult:
    assistant_message: str
    state: dict[str, Any]
    tool_actions: list[dict[str, Any]]


def welcome_message() -> str:
    return WELCOME_MESSAGE


def initial_state() -> dict[str, Any]:
    return _initial_state()


def run_onboarding_step(
    *,
    state: dict[str, Any],
    user_message: str,
) -> OnboardingResult:
    """Deterministic onboarding used by tests + UI.

    Phases are integers 1–5 (see ``onboarding_gate.initial_state``).
    """
    assistant_message, st, tool_actions = run_onboarding_gate(
        state=state, user_message=user_message
    )
    return OnboardingResult(
        assistant_message=assistant_message, state=st, tool_actions=tool_actions
    )
