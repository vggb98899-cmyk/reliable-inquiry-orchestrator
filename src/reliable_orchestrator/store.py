from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from .models import ExecutionPlan, ObjectState


class StateStore:
    def __init__(self, path: str | Path = ":memory:"):
        self.connection = sqlite3.connect(str(path))
        self.connection.row_factory = sqlite3.Row
        self._initialize()

    def _initialize(self) -> None:
        self.connection.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS event_receipt(
            event_id TEXT PRIMARY KEY, received_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS execution_plan(
            plan_id TEXT PRIMARY KEY, event_id TEXT UNIQUE NOT NULL,
            snapshot_id TEXT NOT NULL, target TEXT NOT NULL,
            item_keys_json TEXT NOT NULL, plan_hash TEXT NOT NULL,
            created_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS object_result(
            plan_id TEXT NOT NULL, object_key TEXT NOT NULL,
            state TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '',
            updated_at REAL NOT NULL, PRIMARY KEY(plan_id, object_key));
        CREATE TABLE IF NOT EXISTS side_effect_intent(
            idempotency_key TEXT PRIMARY KEY, plan_id TEXT NOT NULL,
            object_key TEXT NOT NULL, state TEXT NOT NULL,
            created_at REAL NOT NULL, updated_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS lease(
            lease_name TEXT PRIMARY KEY, owner TEXT NOT NULL, expires_at REAL NOT NULL);
        """)
        self.connection.commit()

    def record_event_once(self, event_id: str) -> bool:
        cursor = self.connection.execute(
            "INSERT OR IGNORE INTO event_receipt VALUES(?,?)", (event_id, time.time())
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def save_plan(self, plan: ExecutionPlan) -> None:
        self.connection.execute(
            "INSERT INTO execution_plan VALUES(?,?,?,?,?,?,?)",
            (plan.plan_id, plan.event_id, plan.snapshot_id, plan.target,
             json.dumps(plan.item_keys), plan.plan_hash, time.time()),
        )
        self.connection.executemany(
            "INSERT INTO object_result VALUES(?,?,?,'',?)",
            [(plan.plan_id, key, ObjectState.PLANNED.value, time.time()) for key in plan.item_keys],
        )
        self.connection.commit()

    def plan_for_event(self, event_id: str) -> sqlite3.Row | None:
        return self.connection.execute(
            "SELECT * FROM execution_plan WHERE event_id=?", (event_id,)
        ).fetchone()

    def object_state(self, plan_id: str, object_key: str) -> ObjectState:
        row = self.connection.execute(
            "SELECT state FROM object_result WHERE plan_id=? AND object_key=?",
            (plan_id, object_key),
        ).fetchone()
        if row is None:
            raise KeyError(object_key)
        return ObjectState(row[0])

    def set_object_state(self, plan_id: str, object_key: str,
                         state: ObjectState, detail: str = "") -> None:
        self.connection.execute(
            "UPDATE object_result SET state=?,detail=?,updated_at=? WHERE plan_id=? AND object_key=?",
            (state.value, detail, time.time(), plan_id, object_key),
        )
        self.connection.commit()

    def reserve_intent(self, plan_id: str, object_key: str) -> bool:
        key = f"{plan_id}:{object_key}"
        cursor = self.connection.execute(
            "INSERT OR IGNORE INTO side_effect_intent VALUES(?,?,?,'RESERVED',?,?)",
            (key, plan_id, object_key, time.time(), time.time()),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def commit_intent(self, plan_id: str, object_key: str, state: str) -> None:
        self.connection.execute(
            "UPDATE side_effect_intent SET state=?,updated_at=? WHERE idempotency_key=?",
            (state, time.time(), f"{plan_id}:{object_key}"),
        )
        self.connection.commit()

    def results(self, plan_id: str) -> list[sqlite3.Row]:
        return self.connection.execute(
            "SELECT * FROM object_result WHERE plan_id=? ORDER BY object_key", (plan_id,)
        ).fetchall()

    def acquire_lease(self, name: str, owner: str, ttl_seconds: int, now: float | None = None) -> bool:
        timestamp = time.time() if now is None else now
        self.connection.execute("DELETE FROM lease WHERE lease_name=? AND expires_at<=?", (name, timestamp))
        cursor = self.connection.execute(
            "INSERT OR IGNORE INTO lease VALUES(?,?,?)",
            (name, owner, timestamp + ttl_seconds),
        )
        self.connection.commit()
        return cursor.rowcount == 1

    def close(self) -> None:
        self.connection.close()
