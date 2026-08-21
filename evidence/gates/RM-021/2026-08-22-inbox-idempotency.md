# RM-021 Evidence - Inbox and Idempotent Consumer Semantics

Date: 2026-08-22

## Acceptance evidence

- `InboxMessage` uses event ID as the durable deduplication key and models
  received, processing, processed, retryable, and dead-letter states.
- `InboxProcessor` records/claims before invoking the handler, acknowledges only
  after durable processing state, ignores already processed duplicates, and
  stores bounded retry/error state for poison messages.
- Flyway V5 and `JpaInboxRepositoryAdapter` persist the full event envelope and
  diagnostic attempt/error fields in PostgreSQL.

## Local gate

Command: `scripts/full-gate.ps1 -Infrastructure`

Result: PASS - control plane, Compose health, Java 30 tests, Python 16 tests,
100% statement/branch coverage, and 4 schemas / 12 contract fixtures.

## Real infrastructure gate

Commands: `scripts/infra.ps1 -Action up`, `scripts/business-api.ps1 -Action run`,
PostgreSQL probes through `docker compose exec postgres psql`, then clean
shutdown.

Results:

- PostgreSQL 18.6 migrated from V4 to V5 and Hibernate validation completed.
- RabbitMQ and Redis were healthy; `/actuator/health` returned `UP`.
- A poison Inbox row persisted as `DEAD_LETTER` with attempts `3` and diagnostic
  error `poison`, then was deleted as probe cleanup.
