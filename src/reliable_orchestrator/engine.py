from __future__ import annotations

import hashlib
import json
import time
import uuid

from .adapters import ExternalAction
from .errors import (BlastRadiusExceeded, DuplicateBusinessKey, ReadbackMismatch,
                     SchemaMismatch, SnapshotExpired, TargetMismatch, UnknownSideEffect)
from .models import ActionResult, ExecutionPlan, ObjectState, RunSummary, Snapshot
from .store import StateStore


class Orchestrator:
    SUPPORTED_SCHEMA = 1

    def __init__(self, store: StateStore, adapter: ExternalAction, *, target: str,
                 snapshot_max_age_seconds: int = 300, max_actions: int = 25):
        self.store = store
        self.adapter = adapter
        self.target = target
        self.snapshot_max_age_seconds = snapshot_max_age_seconds
        self.max_actions = max_actions

    def create_plan(self, event_id: str, snapshot: Snapshot, now: float | None = None) -> ExecutionPlan:
        existing = self.store.plan_for_event(event_id)
        if existing:
            return ExecutionPlan(existing["plan_id"], existing["event_id"], existing["snapshot_id"],
                                 existing["target"], tuple(json.loads(existing["item_keys_json"])),
                                 existing["plan_hash"])
        timestamp = time.time() if now is None else now
        if timestamp - snapshot.created_at > self.snapshot_max_age_seconds:
            raise SnapshotExpired(snapshot.snapshot_id)
        if snapshot.schema_version != self.SUPPORTED_SCHEMA:
            raise SchemaMismatch(str(snapshot.schema_version))
        if snapshot.target != self.target:
            raise TargetMismatch(snapshot.target)
        keys = tuple(item.object_key for item in snapshot.items)
        if any(not key.strip() for key in keys):
            raise ValueError("OBJECT_KEY_REQUIRED")
        if len(keys) != len(set(keys)):
            raise DuplicateBusinessKey("snapshot contains duplicate object keys")
        if len(keys) > self.max_actions:
            raise BlastRadiusExceeded(f"{len(keys)}>{self.max_actions}")
        canonical = json.dumps({"event": event_id, "snapshot": snapshot.snapshot_id,
                                "target": snapshot.target, "keys": keys}, sort_keys=True)
        plan = ExecutionPlan(uuid.uuid4().hex, event_id, snapshot.snapshot_id, snapshot.target,
                             keys, hashlib.sha256(canonical.encode()).hexdigest())
        if not self.store.record_event_once(event_id):
            raise RuntimeError("EVENT_RECEIPT_CONFLICT")
        self.store.save_plan(plan)
        return plan

    def execute(self, plan: ExecutionPlan, snapshot: Snapshot) -> RunSummary:
        if tuple(item.object_key for item in snapshot.items) != plan.item_keys:
            raise ValueError("IMMUTABLE_PLAN_MISMATCH")
        for item in snapshot.items:
            state = self.store.object_state(plan.plan_id, item.object_key)
            if state in {ObjectState.CONFIRMED, ObjectState.NOOP, ObjectState.REJECTED}:
                continue
            if state == ObjectState.UNKNOWN:
                raise UnknownSideEffect(item.object_key)
            if not self.store.reserve_intent(plan.plan_id, item.object_key):
                self.store.set_object_state(plan.plan_id, item.object_key, ObjectState.UNKNOWN,
                                            "existing uncommitted intent")
                raise UnknownSideEffect(item.object_key)
            self.store.set_object_state(plan.plan_id, item.object_key, ObjectState.INTENT_RECORDED)
            result = self.adapter.apply(item, f"{plan.plan_id}:{item.object_key}")
            if result == ActionResult.UNKNOWN:
                self.store.commit_intent(plan.plan_id, item.object_key, "UNKNOWN")
                self.store.set_object_state(plan.plan_id, item.object_key, ObjectState.UNKNOWN,
                                            "external outcome cannot be proven")
                raise UnknownSideEffect(item.object_key)
            if result == ActionResult.REJECTED:
                self.store.commit_intent(plan.plan_id, item.object_key, "REJECTED")
                self.store.set_object_state(plan.plan_id, item.object_key, ObjectState.REJECTED)
                continue
            if not self.adapter.read_back(item):
                self.store.commit_intent(plan.plan_id, item.object_key, "UNKNOWN")
                self.store.set_object_state(plan.plan_id, item.object_key, ObjectState.UNKNOWN,
                                            "read-back mismatch")
                raise ReadbackMismatch(item.object_key)
            self.store.commit_intent(plan.plan_id, item.object_key, "CONFIRMED")
            self.store.set_object_state(plan.plan_id, item.object_key, ObjectState.CONFIRMED)
        return self.summary(plan.plan_id)

    def summary(self, plan_id: str) -> RunSummary:
        counts = {state: 0 for state in ObjectState}
        for row in self.store.results(plan_id):
            counts[ObjectState(row["state"])] += 1
        return RunSummary(plan_id, counts[ObjectState.CONFIRMED], counts[ObjectState.NOOP],
                          counts[ObjectState.REJECTED], counts[ObjectState.UNKNOWN])
