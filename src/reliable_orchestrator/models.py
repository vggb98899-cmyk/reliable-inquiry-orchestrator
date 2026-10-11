from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ActionResult(str, Enum):
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class Command(str, Enum):
    EXECUTE = "EXECUTE"
    PREVIEW = "PREVIEW"


class ObjectState(str, Enum):
    PLANNED = "PLANNED"
    INTENT_RECORDED = "INTENT_RECORDED"
    CONFIRMED = "CONFIRMED"
    NOOP = "NOOP"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class WorkItem:
    object_key: str
    target: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class Snapshot:
    snapshot_id: str
    created_at: float
    schema_version: int
    target: str
    items: tuple[WorkItem, ...]


@dataclass(frozen=True)
class ExecutionPlan:
    plan_id: str
    event_id: str
    snapshot_id: str
    target: str
    item_keys: tuple[str, ...]
    plan_hash: str


@dataclass(frozen=True)
class RunSummary:
    plan_id: str
    confirmed: int
    noop: int
    rejected: int
    unknown: int
