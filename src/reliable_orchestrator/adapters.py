from __future__ import annotations

from typing import Protocol

from .models import ActionResult, WorkItem


class ExternalAction(Protocol):
    def apply(self, item: WorkItem, idempotency_key: str) -> ActionResult: ...

    def read_back(self, item: WorkItem) -> bool: ...


class MockExternalAction:
    """Deterministic offline adapter used by examples and tests."""

    def __init__(self, outcomes: dict[str, ActionResult] | None = None,
                 readback: dict[str, bool] | None = None):
        self.outcomes = outcomes or {}
        self.readback = readback or {}
        self.calls: list[tuple[str, str]] = []

    def apply(self, item: WorkItem, idempotency_key: str) -> ActionResult:
        self.calls.append((item.object_key, idempotency_key))
        return self.outcomes.get(item.object_key, ActionResult.CONFIRMED)

    def read_back(self, item: WorkItem) -> bool:
        return self.readback.get(item.object_key, True)
