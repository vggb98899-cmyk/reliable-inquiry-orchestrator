from __future__ import annotations

import time


def health_payload(*, started_at: float, database_ok: bool, worker_alive: bool) -> dict[str, object]:
    ready = database_ok and worker_alive
    return {"status": "ready" if ready else "degraded", "ready": ready,
            "database": database_ok, "worker": worker_alive,
            "uptime_seconds": max(0, round(time.time() - started_at, 3))}
