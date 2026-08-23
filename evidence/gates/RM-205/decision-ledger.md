# RM-205 Decision Ledger Evidence

Date: 2026-08-23

## Executable evidence

- `./scripts/business-api.ps1 -Action test`
  - Maven BUILD SUCCESS
  - 66 tests, 0 failures, 0 errors
  - Flyway V12 and Hibernate schema validation passed
- `BusinessApiApplicationTests.advancedDispatchAssignmentIsVersionedAuditedAndIdempotent`
  - one stable `decision_id` (`requestId`) is persisted for the committed dispatch
  - row records `WALL`, `dispatch-api:v1`, strategy/version, and canonical input/output snapshot fields
  - repeated assignment replays without another ledger row; changed idempotency payload remains a conflict
- `DispatchDecisionLedgerTests`
  - simulated clock domain is rejected for durable live dispatch records
  - SHA-256 digests and 64 KiB snapshot bounds are enforced

## Data and authority boundary

V12 creates `routemind.dispatch_decision_ledger` in PostgreSQL with a unique decision
ID and idempotency key, content digests, bounded snapshots, and order index. The
record is written from the Java assignment transaction after the authoritative order
transition and lease commit. Python remains compute authority and Java remains
business/ledger authority. No Kafka, data lake, Redis-only record, or synchronous
object-store dependency was introduced.

## Residual scope

The current live v1 request has compact compute metadata, so the snapshots preserve
the bounded fields available at commit time. An asynchronous archival adapter for
larger payloads is intentionally staged after this hardening gate; its content
address must continue to reference these durable snapshot digests.
