# RM-030 Evidence: Dispatch Registry and Nearest Baseline

Date: 2026-08-22

## Gates

- `scripts/compute-api.ps1 -Action check`: PASS.
- 23 Python tests passed with 100% statement and branch coverage.
- Ruff, strict mypy, and all 4 schemas / 12 contract fixtures passed.
- Existing domain boundary checks remain green: domain imports only the
  standard library; application depends inward on domain contracts.

## Behavior

- `StrategyRegistry` registers strategies by stable name, rejects duplicates,
  supports lookup and comparison, and rejects inconsistent strategy results.
- Strategies expose a version and produce the immutable
  `DispatchProblem`/`DispatchDecision` interface. Registry results record
  monotonic solve latency, candidate count, and assignment status.
- `NearestStrategy` computes Haversine distance in kilometres and ranks by
  `(distance_km, courier_id)`, making equal-distance choices deterministic.
- Empty candidate sets produce an explicit unassigned decision with a null
  score and the `no eligible courier` rationale.
