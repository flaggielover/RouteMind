# RM-206 Solver Verification Evidence

## Scope

Implemented an independent verification kernel in
`services/compute-api/src/routemind_compute/application/verification.py`.
Single-request dispatch checks independently recompute candidate membership,
capacity, state, service risk, travel-time validity, availability and delivery
windows, feasibility, and known strategy objectives. VRPTW checks independently
recompute route membership, stop uniqueness, vehicle existence, capacity,
service and time-window timing, vehicle availability, optional return-to-depot
travel, explicit unassigned semantics, route travel, and aggregate objective.

`StrategyRegistry.solve` and `VrptwStrategy.solve` reject invalid output with
`SolverOutputInvalidError`; API routes emit structured `solver_output_invalid`
reasons and never return the invalid decision as success.

## Maturity labels

The strategy catalog exposes explicit labels: nearest, weighted-greedy,
hungarian and bounded vrptw are `BASELINE`; minimum-cost-flow and
partitioned-assignment are `ENGINEERING`. See ADR-0007 for the supported scope,
complexity, limitations, and fallback semantics.

## Executed evidence

```text
.\scripts\compute-api.ps1 -Action check
```

Result: Ruff, formatting, mypy, contract validation, and 155 Python tests
passed. Coverage: 95.78% (threshold 95%). Focused verifier/API/VRPTW suites
passed. GitHub Actions CI will be observed after the checkpoint is pushed.

## Deliberate limits

The kernel is an executable consistency and feasibility gate, not a theorem
prover. Travel is recomputed through the injected provider boundary; providers
remain responsible for their own route-data provenance and failure behavior.
