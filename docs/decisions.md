# Design decisions

## ADR-001 — Immutable plans

**Decision:** freeze ordered object keys and hash the canonical plan.

**Why:** rescanning during recovery can silently change scope and cause new external actions.

## ADR-002 — Persist intent before action

**Decision:** reserve an idempotency key before calling an external adapter.

**Why:** a process can crash after the click/write but before recording success. An existing unresolved intent is treated as uncertain, not safe to retry.

## ADR-003 — UNKNOWN stops automation

**Decision:** an uncertain side effect is terminal for automatic processing.

**Why:** duplicate irreversible actions are usually worse than a visible manual reconciliation step.

## ADR-004 — Read-back is part of success

**Decision:** adapter return success plus read-back confirmation is required.

**Why:** transport acknowledgement does not prove the business target contains the intended result.

## ADR-005 — Retry reads, not writes

**Decision:** limited retries exist only for explicitly transient read errors.

**Why:** retrying a write after a timeout can duplicate side effects.

## ADR-006 — Independent public implementation

**Decision:** implement generic mechanisms from first principles with mocks.

**Why:** preserve engineering depth without publishing employer code, data, selectors, infrastructure, or business rules.
