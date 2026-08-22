# RM-121 Merchant Preparation Workflow Evidence

## Scope

Merchant preparation is implemented as Java-owned lifecycle commands. The web
merchant surface never writes PostgreSQL directly and demo/replay sources keep
commands disabled.

## Executable evidence

- `./scripts/full-gate.ps1` passed: Java 59 tests, Python 59 tests at 96.13%
  coverage, 5 schemas/15 fixtures, Web 31 unit tests/build.
- `apps/web`: `npm run test:e2e` passed 16 desktop/mobile Playwright tests,
  including axe accessibility checks.
- `./scripts/business-api.ps1 -Action resilience` passed the focused 10-test
  API gate, including the merchant multi-step transition journey.

## Verified behavior

- Java lifecycle now supports `CONFIRMED -> PREPARING -> READY_FOR_PICKUP` and
  dispatch can assign from `READY_FOR_PICKUP`.
- Merchant authorization is explicit for preparation and ready transitions;
  merchant cannot assign orders.
- Flyway migration `V8__expand_merchant_order_statuses.sql` updates the durable
  order status constraint.
- JPA order persistence reuses existing transition audit rows and only appends
  new transitions, preserving the unique `(order_id, sequence_number)` key across
  successive commands.
- The merchant UI exposes Accept order, Start preparation, and Mark ready using
  expected-version/idempotency command calls, with trace, conflict, retry, and
  unavailable states visible.
- Queue counts and readiness timing are snapshot-derived; missing prep metrics
  are labeled `Unavailable` rather than fabricated.
