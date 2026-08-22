# RM-155 Digital Twin Control and Replay API

Date: 2026-08-23

## Implemented boundary

- `TwinControlService` is a bounded, process-local Python simulation owner
  around the existing `ScenarioKernel`; it does not write Java durable state,
  PostgreSQL, RabbitMQ, or Redis.
- `POST /api/v1/twin/control` supports `start`, `pause`, `resume`, `step`,
  `reset`, `speed`, `scenario`, `seed`, and `strategy`. `GET
  /api/v1/twin/state` is read-only and exposes the current simulation state.
- Commands are bounded by scenario/strategy/seed/speed/step validation. A
  caller-supplied `command_id` gives a recent idempotency window: identical
  repeats return the original result with `replayed=true`, while payload reuse
  conflicts return HTTP 409. Unknown strategies return HTTP 400 and semantic
  command violations return HTTP 422.
- Simulated time advances only through `step` and is scaled by the explicit
  speed value; wall-clock time is never used for state. Responses carry status,
  simulated seconds/tick, generation, strategy version, events, and a
  canonical SHA-256 replay digest.
- Scenario manifests are deterministic and seeded, and scenario assignment
  events retain the underlying `ScenarioKernel` replay digest. No new network
  service was introduced.

## Evidence

- Focused tests cover all nine command actions, bounded validation, running /
  paused / completed transitions, deterministic scenario changes, replay digest
  stability, duplicate command replay, idempotency conflicts, command/event
  identity contracts, history bounds, and API state/error mappings.
- `./scripts/compute-api.ps1 -Action check` passes 139 tests at 95.71% total
  coverage, Ruff/format/mypy, contract validation, and 5 schemas/15 fixtures.
- `./scripts/full-gate.ps1` passes Java 60 tests, Python 139 tests at 95.71%,
  Web format/lint/typecheck, 38 unit tests, production build, and 5
  schemas/15 fixtures. Browser smoke remains 17 passed with one desktop-only
  skip.
- Design checkpoint Actions run `32604205211` passed all five jobs; the
  implementation checkpoint still requires its own remote Evidence Gate.

## Gate decision

Local L3 twin API, L4 control, and L5 control-failure evidence is complete.
Remote GitHub Actions validation is required before `TASK_GRAPH.yaml` changes
RM-155 to `passed`.
