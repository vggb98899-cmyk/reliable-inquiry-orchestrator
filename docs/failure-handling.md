# Failure handling

| Failure | Classification | Automatic behavior |
|---|---|---|
| Snapshot too old | Pre-action gate | Reject plan |
| Wrong schema or target | Pre-action gate | Reject plan |
| Duplicate/missing key | Pre-action gate | Reject plan |
| Too many actions | Blast-radius gate | Reject plan |
| Transient read timeout | Retryable read | Retry within limit |
| Non-retryable read error | Permanent | Stop immediately |
| External action rejected | Confirmed rejection | Persist `REJECTED`, continue |
| External outcome uncertain | Duplicate-risk boundary | Persist `UNKNOWN`, stop |
| Read-back mismatch | Duplicate-risk boundary | Persist `UNKNOWN`, stop |
| Crash with reserved intent | Recovery boundary | Do not repeat; require reconciliation |
| Lease already held | Concurrency gate | Another worker wins |

The core rule is simple: no evidence means no claim of success, and uncertainty after an external action never becomes permission to retry.
