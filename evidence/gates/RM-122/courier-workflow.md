# RM-122 Courier Shift and Delivery Workflow

Date: 2026-08-22

## Scope

- Java owns durable courier shift state in `routemind.courier_shifts` and durable
  command deduplication in `routemind.courier_command_idempotency`.
- Courier shift (`ONLINE`/`OFFLINE`), location, and order lifecycle commands use
  actor authorization, expected versions where applicable, stable idempotency
  keys, trace metadata, and transactional outbox events.
- Order lifecycle supports the courier audit path `ASSIGNED -> ACCEPTED -> ARRIVED
  -> PICKED_UP -> DELIVERED` while retaining the existing direct pickup transition
  for backward-compatible dispatch flows.
- Web CourierView exposes go online/offline, send location, accept task, arrive at
  merchant, confirm pickup, and complete delivery actions. Demo and replay writes
  remain disabled.
- Redis GEO is optional. When the projection is unavailable, the durable location
  write remains accepted, the command returns `DEGRADED`, and the UI marks the
  courier projection as degraded. Stale locations relative to the live snapshot
  are also surfaced as degraded and disable writes.

## Evidence

- `services/business-api`: `scripts/full-gate.ps1` passed with Java 60 tests,
  including the courier MockMvc golden path, Flyway v9, idempotent shift replay,
  degraded location projection, and courier order transitions.
- `services/compute-api`: 59 pytest tests passed with 96.13% coverage; ruff,
  mypy, contract validation, and schema/fixture validation passed.
- `apps/web`: `npm run check` passed with 34 unit tests and production build;
  `scripts/web.ps1 -Action e2e` passed all 16 Playwright tests across desktop and
  mobile role routes.
- Realtime projection tests cover courier location updates, shift status updates,
  stale/degraded projection handling, and forward-only order lifecycle updates.

## Gate decision

Local L3 courier API and L4 courier golden-path gates pass. Remote GitHub Actions
validation is required before treating this checkpoint as fully validated.
