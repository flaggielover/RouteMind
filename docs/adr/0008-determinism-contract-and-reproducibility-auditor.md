# ADR-0008: Determinism Contract and Reproducibility Auditor

## Status

Accepted for RM-207.

## Decision

Determinism is declared per subsystem rather than inferred from a passing
single run:

- `DETERMINISM_CRITICAL` requires the canonical digest to match across the
  repeated seeded run.
- `DETERMINISTIC_IF_CONFIGURED` requires the same result when the recorded
  strategy/configuration/seed is supplied.
- `NONDETERMINISTIC_ALLOWED` is observable and recorded, but a changed digest
  is not treated as a correctness failure.

The Compute API's `audit_scenario` runs the same `ScenarioManifest` twice and
records the seed, normalized configuration, bounded runtime environment, and
both output digests. Critical and configured contracts raise
`DeterminismViolationError` on drift. The `compute-api.ps1 check` gate invokes
`scripts/determinism_gate.py`, so the Python CI job fails on an unclassified
determinism regression.

Operational request/trace UUIDs and wall-clock response timestamps remain
`NONDETERMINISTIC_ALLOWED`; they are not part of simulation/replay digests.
Seeded simulation, RouteBench, and canonical experiment outputs remain
determinism-critical or configured according to their recorded inputs.

## Consequences

The contract makes reproducibility evidence executable and records enough
environment context to interpret a digest. It does not claim bitwise equality
for explicitly allowed operational nondeterminism, nor does it make a
distributed clock or a global random service part of the architecture.
