# RM-218 Location Integrity and Hotspot Evidence

Date: 2026-08-24
Implementation checkpoint: a61b559
GitHub Actions: PASS - run 32651238530 (all five jobs)

## Scope

The Python compute domain compares sequenced courier reports and emits explicit
`HEALTHY`, `DEGRADED`, `SUSPECT`, or `STALE` states. Signals cover duplicate and
missing sequences, event-time regression, impossible speed/teleport, stale or
offline reports, and ingestion lag. The endpoint and response label these as
operational signals, never disciplinary decisions.

Hotspots are deterministic grid aggregates requiring at least three distinct
couriers per cell by default. Courier identifiers and raw trajectories are
excluded from the response; request and library bounds prevent unbounded
analytical work.

## Local evidence

- `./scripts/compute-api.ps1 check` - PASS, 191 Python tests at 95.42% coverage,
  Ruff, format, strict mypy, 6 schemas, 18 fixtures, determinism, archive,
  marts, and semantic metrics gates.
- `./scripts/verify.ps1` - PASS repository integrity and task/evidence rules.
- `tests/test_location_integrity.py` - PASS direct status precedence, duplicate
  handling, impossible-speed signal, bounded hotspot k-anonymity, and digest
  behavior.
- `tests/test_api.py` - PASS `/api/v1/locations/integrity` trace propagation,
  signal response, and privacy-bounded hotspot response.

## Boundary and limitations

No Java authority, Redis projection, dispatch eligibility, or courier discipline
is changed by this read-oriented compute endpoint. Thresholds are configured
inputs, not production calibration evidence. Sparse cells are intentionally
omitted when the minimum distinct-courier threshold is not met.

## Remote validation

GitHub Actions run `32651238530` passed the Java, control-plane/Compose,
Python/contracts, Web static/unit/browser, and bounded degradation/resilience
jobs for checkpoint `a61b559`.
