# RM-011 Evidence - Order Lifecycle State Machine

Date: 2026-08-21

## Acceptance evidence

- `OrderStatus` defines the explicit path `CREATED -> CONFIRMED -> ASSIGNED ->
  PICKED_UP -> DELIVERED`; cancellation is allowed only from the first three
  non-terminal states.
- The domain rejects forbidden, repeated, stale-version, non-advancing-time,
  and terminal-state transitions.
- Each accepted transition creates an immutable sequence-numbered
  `OrderTransition` audit record with actor and timestamp.
- Flyway V3 owns `orders` and `order_transitions`; the JPA adapter persists both
  in one transaction with an optimistic `@Version` column and a unique
  `(order_id, sequence_number)` audit constraint.

## Local gate

Command: `scripts/business-api.ps1 -Action test`

Result: PASS - 22 tests, 0 failures, 0 errors, including architecture checks,
Flyway versions 1-3, three domain lifecycle suites, repository round trip, and
transition audit persistence.

## Real PostgreSQL gate

Commands: `scripts/infra.ps1 -Action up`, `scripts/business-api.ps1 -Action run`,
and PostgreSQL probes through `docker compose exec postgres psql`.

Results:

- PostgreSQL 18.6 accepted Flyway migration from V2 to V3.
- Hibernate `ddl-auto=validate` completed and the application started on port
  18080.
- A `CONFIRMED` order and its `CREATED -> CONFIRMED` transition were inserted;
  a grouped query returned one audit row. Probe data was deleted.
- Application and infrastructure were stopped cleanly; persistent volumes were
  preserved.
