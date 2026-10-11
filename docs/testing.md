# Testing strategy

The suite is fully offline and uses an in-memory SQLite database plus a deterministic mock adapter.

Covered scenarios:

- normal confirmed execution;
- repeated event idempotency;
- missing and duplicate business keys;
- target mismatch;
- schema incompatibility;
- stale snapshot rejection;
- immutable-plan conflict;
- blast-radius limit;
- bounded transient read retry;
- immediate stop for non-retryable errors;
- uncertain write outcome with no second attempt;
- read-back mismatch;
- recovery that skips confirmed objects;
- unresolved-intent crash recovery;
- scheduler lease competition and expiry;
- API-style health payload.

Production history and production test totals are intentionally not included. Only tests executed from this repository may be reported as public test results.
