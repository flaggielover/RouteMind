# P8 Request Rate-Limit and Input Protection Contract

## Goal

Bound abusive or malformed requests before they reach durable command state,
while keeping authorization and business invariants in Java. The first
contract is deterministic and adapter-neutral: it computes an admission result
from a normalized request descriptor and an externally supplied usage snapshot.

## Policy invariants

`RequestPolicy` binds a policy version, key scope (`principal`, `client`, or
`endpoint`), fixed window seconds, maximum requests, burst allowance, maximum
body bytes, maximum field count, and maximum field length. Limits are positive,
policy versions are explicit, and a request cost must be positive. The policy
does not store counters in the contract; Redis or an edge limiter may provide a
hot counter, but PostgreSQL and Java remain authoritative for business state.

`RequestDescriptor` normalizes endpoint, method, key, body size, field count,
field lengths, UTF-8 validity, control-character status, and idempotency key.
Secrets and raw bodies are not part of decision evidence.

## Decision policy

`evaluate()` returns `allow`, `throttle`, or `reject` with stable reason codes:

- malformed method/key/encoding/control characters or missing idempotency key
  for a command -> `reject`;
- body, field, or field-length limit -> `reject`;
- invalid/negative usage snapshot -> `reject`;
- usage at or above the window plus burst budget -> `throttle` with deterministic
  retry-after seconds;
- otherwise -> `allow`.

The evaluator is read-only and does not mint authorization, mutate counters,
write PostgreSQL, or acknowledge a command. Retries and idempotency remain
explicit Java/Outbox concerns.

## Validation boundary

Tests will cover canonical policy digests, boundary thresholds, malformed input,
deterministic retry-after, command idempotency requirements, and no-write
behavior. Distributed counter atomicity, WAF/bot mitigation, credential
reputation, production quotas, and load validation remain external gates.
