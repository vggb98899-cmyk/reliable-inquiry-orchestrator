import time

import pytest

from reliable_orchestrator.adapters import MockExternalAction
from reliable_orchestrator.engine import Orchestrator
from reliable_orchestrator.errors import (BlastRadiusExceeded, DuplicateBusinessKey,
                                          ReadbackMismatch, SchemaMismatch,
                                          SnapshotExpired, TargetMismatch,
                                          UnknownSideEffect)
from reliable_orchestrator.models import ActionResult, ObjectState, Snapshot, WorkItem
from reliable_orchestrator.store import StateStore


def snapshot(*keys: str, created_at: float | None = None, schema: int = 1,
             target: str = "mock-channel") -> Snapshot:
    return Snapshot("snapshot-1", created_at or time.time(), schema, target,
                    tuple(WorkItem(key, target, {"value": key}) for key in keys))


def setup_engine(adapter=None, **kwargs):
    store = StateStore()
    return store, Orchestrator(store, adapter or MockExternalAction(),
                               target="mock-channel", **kwargs)


def test_success_path_and_readback():
    adapter = MockExternalAction()
    store, engine = setup_engine(adapter)
    current = snapshot("A", "B")
    plan = engine.create_plan("event-1", current)
    summary = engine.execute(plan, current)
    assert summary.confirmed == 2
    assert [call[0] for call in adapter.calls] == ["A", "B"]
    assert all(store.object_state(plan.plan_id, key) == ObjectState.CONFIRMED for key in ("A", "B"))


def test_event_idempotency_returns_same_plan_and_does_not_duplicate_rows():
    store, engine = setup_engine()
    current = snapshot("A")
    first = engine.create_plan("event-1", current)
    second = engine.create_plan("event-1", current)
    assert first == second
    assert len(store.results(first.plan_id)) == 1


def test_missing_key_is_rejected():
    _, engine = setup_engine()
    with pytest.raises(ValueError, match="OBJECT_KEY_REQUIRED"):
        engine.create_plan("event", snapshot(""))


def test_duplicate_key_is_rejected():
    _, engine = setup_engine()
    with pytest.raises(DuplicateBusinessKey):
        engine.create_plan("event", snapshot("A", "A"))


def test_target_mismatch_is_rejected():
    _, engine = setup_engine()
    with pytest.raises(TargetMismatch):
        engine.create_plan("event", snapshot("A", target="other"))


def test_schema_mismatch_is_rejected():
    _, engine = setup_engine()
    with pytest.raises(SchemaMismatch):
        engine.create_plan("event", snapshot("A", schema=2))


def test_expired_snapshot_is_rejected():
    _, engine = setup_engine(snapshot_max_age_seconds=10)
    with pytest.raises(SnapshotExpired):
        engine.create_plan("event", snapshot("A", created_at=100), now=111)


def test_blast_radius_is_rejected_before_intent():
    store, engine = setup_engine(max_actions=1)
    with pytest.raises(BlastRadiusExceeded):
        engine.create_plan("event", snapshot("A", "B"))
    assert store.connection.execute("SELECT COUNT(*) FROM side_effect_intent").fetchone()[0] == 0


def test_immutable_plan_conflict_is_rejected():
    _, engine = setup_engine()
    original = snapshot("A")
    plan = engine.create_plan("event", original)
    with pytest.raises(ValueError, match="IMMUTABLE_PLAN_MISMATCH"):
        engine.execute(plan, snapshot("B"))


def test_unknown_write_stops_and_is_not_retried():
    adapter = MockExternalAction({"A": ActionResult.UNKNOWN})
    store, engine = setup_engine(adapter)
    current = snapshot("A")
    plan = engine.create_plan("event", current)
    with pytest.raises(UnknownSideEffect):
        engine.execute(plan, current)
    assert len(adapter.calls) == 1
    with pytest.raises(UnknownSideEffect):
        engine.execute(plan, current)
    assert len(adapter.calls) == 1
    assert store.object_state(plan.plan_id, "A") == ObjectState.UNKNOWN

def test_readback_mismatch_becomes_unknown():
    adapter = MockExternalAction(readback={"A": False})
    store, engine = setup_engine(adapter)
    current = snapshot("A")
    plan = engine.create_plan("event", current)
    with pytest.raises(ReadbackMismatch):
        engine.execute(plan, current)
    assert store.object_state(plan.plan_id, "A") == ObjectState.UNKNOWN


def test_rejected_object_does_not_stop_later_objects():
    adapter = MockExternalAction({"A": ActionResult.REJECTED})
    store, engine = setup_engine(adapter)
    current = snapshot("A", "B")
    plan = engine.create_plan("event", current)
    summary = engine.execute(plan, current)
    assert (summary.rejected, summary.confirmed) == (1, 1)
    assert store.object_state(plan.plan_id, "A") == ObjectState.REJECTED


def test_recovery_skips_confirmed_objects():
    adapter = MockExternalAction()
    store, engine = setup_engine(adapter)
    current = snapshot("A", "B")
    plan = engine.create_plan("event", current)
    store.set_object_state(plan.plan_id, "A", ObjectState.CONFIRMED)
    summary = engine.execute(plan, current)
    assert summary.confirmed == 2
    assert [call[0] for call in adapter.calls] == ["B"]


def test_crash_after_intent_reservation_fails_closed():
    adapter = MockExternalAction()
    store, engine = setup_engine(adapter)
    current = snapshot("A")
    plan = engine.create_plan("event", current)
    assert store.reserve_intent(plan.plan_id, "A")
    with pytest.raises(UnknownSideEffect):
        engine.execute(plan, current)
    assert adapter.calls == []
    assert store.object_state(plan.plan_id, "A") == ObjectState.UNKNOWN
