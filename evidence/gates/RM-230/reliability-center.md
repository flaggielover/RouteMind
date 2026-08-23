# RM-230 Reliability Center Evidence

Date: 2026-08-24
Status: validating

## Scope

- Operations exposes a read-only Reliability Center with a bounded timeline,
  invariant matrix, dependency/trace records, and recovery evidence.
- Live states distinguish healthy, degraded, and unavailable; demo/replay are
  fixture states and unavailable reconciliation telemetry stays explicit.
- No autonomous repair or remediation path was added.

## Local evidence

- Web `npm run check`: PASS - 29 test files, 81 tests, lint, typecheck, and Vite
  production build.
- Web Playwright full gate: PASS - 34 tests passed, 2 existing desktop-only
  skips. Live unavailable and stale courier/realtime Axe scenarios pass on
  desktop and mobile.
- Reliability projection tests cover fixture labeling, missing reconciliation,
  live degradation, stale courier detection, stream recovery evidence,
  dependencies, and bounded operator boundaries.

## Remote evidence

Pending checkpoint commit and GitHub Actions run.

## Boundaries

Java reconciliation remains the durable invariant authority. The Web surface
does not infer a healthy report when the reconciliation record is absent, and
trace IDs remain unavailable when no request/ledger identity is attached.
