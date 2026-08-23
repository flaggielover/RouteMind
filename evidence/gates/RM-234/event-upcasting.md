# RM-234 Event Upcasting and Historical Replay Compatibility Evidence

Date: 2026-08-24  
Status: passed

## Implementation

- Compute `HistoricalEvent` parses immutable archived envelopes with explicit
  `WALL`, `SIMULATED`, and `REPLAY` clock domains.
- `EventUpcasterRegistry` enforces declared current versions and one-step,
  additive transitions. The bounded default registry upgrades assignment events
  from v1 to v2 by adding `selected_courier_id` and `selection_source`.
- `POST /api/v1/replay/upcast` is read-only and returns source digest, current
  read-model digest, original version, and the complete upcast path.
- Event ID, event time, clock domain, trace ID, reference-data identity, and
  replay digest are preserved. Unknown type/version, missing transition, and
  invalid output return explicit error codes.

## Local evidence

- `./scripts/compute-api.ps1 check`: PASS - 233 tests, 95.27% total coverage,
  Ruff, format, strict mypy, 6 schemas/18 fixtures, deterministic replay,
  archive, mart, and semantic-metrics gates.
- `tests/test_event_upcasting.py`: 21 focused tests cover identity projection,
  multi-field provenance preservation, malformed envelopes, explicit failures,
  API projection, and unknown-version rejection.

## Remote evidence

Checkpoint: `9fe015d`

GitHub Actions: PASS - run `32661326399`, all five jobs.

## Boundaries

Java remains the durable event and transactional outbox owner. Upcasting only
creates a current read-model projection; it never edits source archives or owns
dispatch correctness.
