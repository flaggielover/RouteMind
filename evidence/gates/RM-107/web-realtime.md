# RM-107 Web Realtime Reconnect and Stale-State Handling

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: `48ef6fa`
- Boundary: browser-side SSE cursor consumer and visible connection status

## Client behavior

`apps/web/src/data/realtime.ts` consumes the v1 event-stream item contract with
canonical decimal cursors compared as `BigInt`, and reconnects through the
bounded `after` cursor query. The client listens to the supported business event
types, retains at most 256 event IDs, and applies an item only when both its
event identity and cursor are newer. Duplicate and out-of-order items are
ignored; a cursor gap or server `stale=true` item stops application and exposes a
stale reason. Invalid contract items expose a degraded stream state.

Connection loss closes the current source and retries with deterministic 250 ms,
500 ms, 1 s, 2 s, and 4 s capped backoff. The topbar labels connecting,
connected, reconnecting, stale, and degraded states. Live data remains live and
unavailable when APIs fail; the client never silently switches to demo data.
Forward order lifecycle events update only higher aggregate versions and cannot
regress a visible status.

## Executable evidence

1. `npm run check` in `apps/web` -> PASS; formatting, ESLint, TypeScript, 13 unit
   tests, and production build.
2. `npm run test:e2e` in `apps/web` -> PASS; 16 desktop/mobile role, viewport,
   and axe accessibility tests.
3. `./scripts/full-gate.ps1` -> PASS; Java 57 tests, Python 59 tests at 96.13%
   coverage, 5 schemas/15 fixtures, and the Web static/unit/build gate.
4. `git diff --check` -> PASS before checkpoint commit.
5. GitHub Actions run `32565914443` -> PASS; all five jobs passed, including
   the Web browser smoke gate.

## Evidence limits

This gate proves deterministic browser consumer behavior with injected EventSource
fixtures and local browser smoke. It does not claim production browser fleet
reliability, multi-tab coordination, load capacity, or a live deployed API.
