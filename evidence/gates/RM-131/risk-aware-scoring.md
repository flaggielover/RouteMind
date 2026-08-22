# RM-131 Capacity, Preparation, and Risk-Aware Scoring

Date: 2026-08-22

## Implemented contract

- The registered `risk-aware` strategy scores the same constrained
  `DispatchProblem` accepted by nearest, weighted-greedy, and Hungarian. It
  combines great-circle distance, pickup-readiness delay, overtime risk, service
  risk, and courier load balance with explicit non-negative weights.
- Strategy version `1.0.0`, weight metadata, score units, and selected component
  values are returned in the decision rationale/metadata. Ties are deterministic
  by score then courier identifier.
- Infeasible candidates remain unassigned with the same explicit constraint
  reasons; risk-aware scoring never silently falls back to an unconstrained
  baseline.

## Evidence

- Compute check passes 69 tests at 96.57% coverage, including risk-aware API
  execution, deterministic component metadata, weight validation, infeasibility,
  and lower-risk selection fixtures.
- Default registry baseline comparison now includes `risk-aware` alongside nearest,
  weighted-greedy, and Hungarian without changing the input problem contract.
- Full available gate passes Java 60 tests, Python 69 tests at 96.57%, Web 38 unit
  tests/build, and 5 schemas/15 contract fixtures.

## Gate decision

Local L2 risk-scoring and L6 baseline-comparison evidence is complete. Remote
Actions validation is required before the task is finally closed.
