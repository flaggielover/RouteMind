# RM-120 Customer Order Workflow Evidence

## Scope

The customer role now uses the Java-owned order command boundary. The browser
does not write PostgreSQL directly and demo/replay sources keep writes disabled.

## Executable evidence

- `services/business-api`: `./scripts/business-api.ps1 -Action test` passed with
  57 tests on the repository JDK 17.0.1.
- `apps/web`: `npm run check` passed with 29 unit tests and a production build.
- `apps/web`: `npm run test:e2e` passed 16 desktop/mobile Playwright tests,
  including role routing and axe accessibility checks.
- `scripts/full-gate.ps1` is the required combined gate for the checkpoint.

## Verified behavior

- `POST /api/v1/orders` is called with `X-Actor: customer`, an explicit
  `Idempotency-Key`, optional correlation context, and receives `X-Trace-Id`.
- Command success exposes order id, lifecycle status, aggregate version, replay
  state, trace id, and the key used for a safe retry.
- Validation, conflict, timeout, and unavailable responses remain explicit; only
  server/timeout failures are marked retryable.
- `order.created` realtime events add a newly created order to an empty live
  snapshot, while forward-only lifecycle updates retain version ordering.
- Customer tracking labels source freshness and distinguishes connected,
  paused, and degraded realtime states.
