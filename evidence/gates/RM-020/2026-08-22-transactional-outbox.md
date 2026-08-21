# RM-020 Evidence - Transactional Outbox Publishing

Date: 2026-08-22

## Acceptance evidence

- `EventEnvelope` validates the existing events/v1 identity, aggregate, trace,
  and payload contract. `OutboxMessage` preserves event ID across retries.
- `OrderCommandService` transitions an order and inserts a pending Outbox row
  under one Spring transaction.
- `OutboxRelay` claims due rows, waits for publisher confirmation, marks success,
  and applies bounded exponential retry on failure.
- PostgreSQL claim queries use pessimistic write locking; Flyway V4 owns the
  durable queue, retry state, event identity, and publication timestamps.
- `RabbitOutboxPublisher` uses RabbitTemplate publisher confirms and the Compose
  RabbitMQ endpoint is configurable through environment variables.

## Local gate

Command: `scripts/full-gate.ps1 -Infrastructure`

Result: PASS - control plane, Compose health, Java 27 tests, Python 16 tests,
100% statement/branch coverage, and 4 schemas / 12 contract fixtures.

## Real infrastructure gate

Commands: `scripts/infra.ps1 -Action up`, `scripts/business-api.ps1 -Action run`,
PostgreSQL probes via `docker compose exec postgres psql`, and clean shutdown.

Results:

- PostgreSQL 18.6 migrated from V3 to V4 and Hibernate validation completed.
- RabbitMQ and Redis were healthy; application RabbitMQ health connected through
  `127.0.0.1:15673` and `/actuator/health` returned `UP`.
- A durable `PENDING` Outbox row with event identity, aggregate identity,
  correlation, trace, and payload fields was inserted and read back.
- Probe data, application process, and containers were cleaned up; persistent
  volumes were preserved.
