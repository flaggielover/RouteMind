# RM-134 Dynamic Insertion

Date: 2026-08-23

## Implemented boundary

- `VrptwRoutePlanner.insert` accepts an immutable `VrpProblem` snapshot, an
  active `VrpRoute`, and one new `VrpStop`; it evaluates every insertion
  position without mutating the existing route or problem.
- Feasible positions are ranked by incremental travel seconds, candidate stop
  sequence, and position. The returned `VrpInsertionDecision` contains a new
  route, insertion position, and incremental cost.
- Rejections are stable: `capacity_insufficient`, `time_window_missed`,
  `vehicle_unavailable_until`, `stop_id_conflict`, `vehicle_not_found`,
  `route_stop_not_found`, `active_route_infeasible`, `stop_limit_exceeded`, and
  `no feasible insertion`.
- The optimizer remains compute-owned and returns a proposed route only; it
  does not mutate Java durable assignments or claim implicit replanning.

## Evidence

- Focused tests cover deterministic middle insertion, zero-cost insertion on a
  verified line fixture, snapshot immutability, capacity and time-window
  rejection, route/vehicle identity guards, and the bounded stop limit.
- `./scripts/compute-api.ps1 -Action check` passes 122 tests at 95.56% coverage,
  Ruff, format, mypy, contract validation, and 5 schemas/15 fixtures.
- `./scripts/full-gate.ps1` passes Java 60 tests, Python 122 tests at 95.56%,
  Web 38 unit tests/build, and 5 schemas/15 fixtures.

## Gate decision

Local L2 dynamic-insertion and L6 insertion-benchmark evidence is complete.
Remote GitHub Actions validation is required before `TASK_GRAPH.yaml` changes
RM-134 to `passed`.
