# RM-171 Failure and Degradation E2E Design

## Goal

Exercise the selected dependency and lifecycle failures against the real local
PostgreSQL/RabbitMQ/Redis/Java/Python stack. The evidence must show durable
truth, idempotency, bounded failure responses, and recovery; it must not turn a
browser fixture or a simulated failure into a live-service claim.

## Scenarios

`scripts/failure-degradation-e2e.ps1` owns one isolated run namespace and keeps
the Compose volumes. It launches the same Java/Python repository entry points
as RM-170, then executes:

1. Redis loss: stop only Redis, write a courier location, require HTTP success
   with `DEGRADED`, and verify the PostgreSQL location remains durable. Restart
   Redis and require the next write to return `PROJECTED`.
2. Compute outage: terminate the Python process, require its health/dispatch
   boundary to be unavailable, and prove Java can still create a durable order.
   Restart Python and require health recovery.
3. RabbitMQ restart: stop RabbitMQ, create a Java order, verify its Outbox row
   is not falsely marked published, restart the broker, and wait for the
   scheduled relay to mark that row `PUBLISHED`.
4. Duplicate event/command: submit the same order create command twice with one
   idempotency key and require a replay response plus exactly one durable order
   and one `order.created` Outbox event for that key.
5. Courier offline: transition a courier to `OFFLINE`, submit an offline Python
   candidate, and require no selected courier plus an explicit offline reason.
   A stale Java shift command must return `409 stale_version`.
6. Dispatch timeout: replace the stopped compute listener with a local bounded
   black-hole listener, require the HTTP caller to time out within its deadline,
   and prove the Java durable command path remains available. This is recorded
   as a caller timeout boundary, not as a successful compute decision.

The script restores Redis, RabbitMQ, and Python in `finally`, terminates child
process trees, and prints service logs on failure. It never removes named
volumes or deletes durable rows.

## Evidence gate

The gate is PASS only when all six scenarios pass in one run, with the run ID,
unique order/courier identifiers, exact response statuses, and recovery probes
recorded in `evidence/gates/RM-171/failure-e2e.md`. Remote Actions must also
pass all configured jobs before the task graph can move to `passed`.
