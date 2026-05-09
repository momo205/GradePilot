from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _noop_replanner_hook_on_class_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid running the full LangGraph replanner during unrelated API tests."""

    import app.routers.classes as classes_router

    async def _noop(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(classes_router, "_fire_replanner_after_write", _noop)
