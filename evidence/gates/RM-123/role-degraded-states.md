# RM-123 Role Command Errors and Degraded States

Date: 2026-08-22

## Implemented contract

- Customer, merchant, and courier Web command adapters expose pending in the role
  surface and classify failures as `conflict`, `validation`, `timeout`, or
  `unavailable`.
- HTTP 409 and stale/idempotency conflicts are non-retryable and retain the trace
  ID and idempotency key. HTTP 400/403/404 are validation failures. HTTP 408 and
  aborts are timeout failures. HTTP 5xx, network failures, and status `0` are
  unavailable/retryable failures.
- Live snapshots with stale courier locations are `degraded`; all role writes are
  disabled and the UI states that commands are temporarily unavailable. Demo and
  replay sources remain explicitly read-only.

## Evidence

- Web unit gate passes with 36 tests, including conflict, timeout, unavailable,
  idempotency-key retention, courier degradation projection, and degraded live
  write protection.
- Existing Java MockMvc command gates prove trace headers, durable idempotency,
  stale-version conflicts, and unavailable courier projection behavior.
- Browser smoke remains green across 16 desktop/mobile role-route tests after the
  error-state changes.

## Gate decision

Local L2 role-error and L5 role-degradation evidence is complete. The full
available gate passes with Java 60 tests, Python 59 tests at 96.13% coverage, Web
36 unit tests/build, 16 Playwright tests, and 5 schemas/15 fixtures. The checkpoint
is pushed for remote Actions validation before the final CI-backed handoff. Remote
Actions run `32574390001` passed all five jobs, including the Web static/unit and
browser smoke gates.
