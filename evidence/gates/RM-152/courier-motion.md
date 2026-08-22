# RM-152 Courier Motion and Service Progress

Date: 2026-08-23

## Implemented boundary

- `CourierRoute` and `MotionStop` are immutable, provider-neutral simulation
  inputs with bounded stop count, unique identities, supported pickup/delivery
  kinds, and finite non-negative service durations.
- `CourierMotionEngine.advance` moves a courier using simulated seconds and the
  existing `TravelTimeProvider`; it never mutates Java durable state. Between
  route start and the requested time it deterministically emits route-start,
  arrival, pickup-start/completed, delivery-start/completed, and route-completed
  events with stable IDs.
- Motion state exposes idle, en-route, servicing, and available statuses,
  active/completed stops, monotonic time, and emitted event IDs so incremental
  advancement is idempotent and replay-safe.
- `CourierLocationProjection.redis_geo_member` returns the Redis `GEOADD`
  ordering `(longitude, latitude, member)`. Redis remains a rebuildable hot
  projection rather than durable business truth.
- `MotionSnapshot.replay_digest` hashes canonical state and event payloads for
  deterministic replay verification.

## Evidence

- Focused tests cover deterministic interpolation, service and delivery event
  sequencing, availability, Redis GEO member ordering, replay equality,
  incremental event emission, replay digest shape, backwards-time rejection,
  route identity checks, bounded stop counts, and invalid stop contracts.
- `./scripts/compute-api.ps1 -Action check` passes 135 tests at 95.46% total
  coverage, Ruff/format/mypy, contract validation, and 5 schemas/15 fixtures.
- `./scripts/full-gate.ps1` passes Java 60 tests, Python 135 tests at 95.46%,
  Web format/lint/typecheck, 38 unit tests, production build, and 5
  schemas/15 fixtures. Browser smoke remains 17 passed with one desktop-only
  skip.

## Gate decision

Local L2 courier-motion and L6 replay evidence is complete. Remote GitHub
Actions validation is required before `TASK_GRAPH.yaml` changes RM-152 to
`passed`.
