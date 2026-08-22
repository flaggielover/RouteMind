# RM-132 Minimum-Cost Flow and Partitioned Assignment

Date: 2026-08-22

## Implemented contract

- `minimum-cost-flow` solves a bounded bipartite request/courier assignment with
  residual shortest paths, rectangular matrices, courier capacity, deterministic
  tie ordering, and stable total cost.
- `partitioned-assignment` groups requests by explicit partition and only exposes
  couriers from the matching zone. Both strategies preserve the existing
  single-order `DispatchStrategy` contract through a one-request batch adapter.
- Capacity exhaustion and constraint rejection return explicit unassigned reasons;
  no infeasible request is silently assigned. Registry results include assignment
  mode, assigned/unassigned counts, strategy version, and measured latency.

## Evidence

- Compute check passes 74 tests at 96.03% coverage, including residual rematching,
  rectangular capacity, zone isolation, deterministic output, infeasibility, and
  registry metadata fixtures.
- Full available gate passes Java 60 tests, Python 74 tests at 96.03%, Web 38 unit
  tests/build, and 5 schemas/15 contract fixtures.

## Gate decision

Local L2 flow-assignment and L6 dispatch-benchmark evidence is complete. Remote
Actions validation is required before the task is finally closed.
