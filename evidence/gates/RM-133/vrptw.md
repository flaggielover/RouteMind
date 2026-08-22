# RM-133 VRP/VRPTW Baseline

Date: 2026-08-23

## Implemented boundary

- `VrpProblem`, `VrpStop`, `VrpVehicle`, `VrpRoute`, and `VrpRoutePlan` define a
  bounded compute-owned route contract with caps of 32 stops and 32 vehicles.
- `VrptwRoutePlanner` uses a deterministic minimum-increment insertion baseline.
  Every candidate insertion is replayed from the vehicle start, applies capacity,
  service duration, waiting/time-window, vehicle availability, and optional
  return-to-depot checks, and orders ties by route/vehicle identifiers.
- `VrptwStrategy` adapts the existing single-request dispatch contract and is
  registered as `vrptw` without moving durable assignment authority from Java.
- Unassigned stops use stable reason codes: `capacity_insufficient`,
  `time_window_missed`, `vehicle_unavailable_until`, and `no feasible route`.
  Travel uses the replaceable deterministic local provider; no paid provider or
  production-scale optimization claim is made.

## Evidence

- Focused VRP/VRPTW tests cover deterministic insertion, a two-stop reference
  baseline, capacity rejection, waiting and missed windows, service/return
  deadlines, invalid provider output, bounded entity validation, empty fleets,
  registry integration, and single-request dispatch adaptation.
- `./scripts/compute-api.ps1 -Action check` passes 119 tests at 95.57% coverage,
  Ruff, format, mypy, contract validation, and 5 schemas/15 fixtures.
- `./scripts/full-gate.ps1` passes Java 60 tests, Python 119 tests at 95.57%,
  Web 38 unit tests/build, and 5 schemas/15 fixtures.

## Gate decision

Local L2 VRPTW and L6 route-correctness evidence is complete. Remote GitHub
Actions validation is required before `TASK_GRAPH.yaml` changes RM-133 to
`passed`.
