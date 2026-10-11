import time

import pytest

from reliable_orchestrator.health import health_payload
from reliable_orchestrator.retry import bounded_read
from reliable_orchestrator.store import StateStore


def test_transient_read_uses_bounded_retry():
    attempts = []

    def read():
        attempts.append(1)
        if len(attempts) < 3:
            raise TimeoutError("transient")
        return "ok"

    assert bounded_read(read, attempts=3) == "ok"
    assert len(attempts) == 3


def test_non_retryable_read_stops_immediately():
    attempts = []

    def read():
        attempts.append(1)
        raise PermissionError("permanent")

    with pytest.raises(PermissionError):
        bounded_read(read, attempts=3)
    assert len(attempts) == 1


def test_lease_competition_and_expiry():
    store = StateStore()
    assert store.acquire_lease("worker", "one", 10, now=100)
    assert not store.acquire_lease("worker", "two", 10, now=105)
    assert store.acquire_lease("worker", "two", 10, now=111)


def test_health_ready_and_degraded():
    started = time.time() - 5
    ready = health_payload(started_at=started, database_ok=True, worker_alive=True)
    degraded = health_payload(started_at=started, database_ok=True, worker_alive=False)
    assert ready["ready"] is True and ready["status"] == "ready"
    assert degraded["ready"] is False and degraded["status"] == "degraded"
