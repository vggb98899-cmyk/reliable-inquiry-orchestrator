from __future__ import annotations

import json
import time

from .adapters import MockExternalAction
from .engine import Orchestrator
from .models import Snapshot, WorkItem
from .store import StateStore


def main() -> None:
    store = StateStore()
    snapshot = Snapshot("demo-snapshot", time.time(), 1, "mock-channel", (
        WorkItem("ORDER-001:ITEM-A", "mock-channel", {"message": "request quote"}),
        WorkItem("ORDER-002:ITEM-B", "mock-channel", {"message": "request quote"}),
    ))
    orchestrator = Orchestrator(store, MockExternalAction(), target="mock-channel")
    plan = orchestrator.create_plan("demo-event", snapshot)
    print(json.dumps(orchestrator.execute(plan, snapshot).__dict__, indent=2))


if __name__ == "__main__":
    main()
