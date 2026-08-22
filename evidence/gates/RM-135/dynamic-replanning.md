# RM-135 Dynamic Replanning Policy

Date: 2026-08-23

## Implemented boundary

- `ReplanTrigger` models arrival, lateness, incident, courier loss, and
  material-change observations with a monotonic simulated timestamp and trace.
- `ReplanMetrics` carries assigned, unassigned, late, active-route, and total
  travel measurements. A proposal is approved only when the lexicographic
  objective improves; before/after snapshots remain in the decision.
- `DynamicReplanningPolicy` is a pure deterministic gate. It returns either a
  `replan-approved` proposal or a hold reason (`debounced`, `cooldown-active`,
  `no-material-improvement`) and an immutable next state with generation.
- The decision declares `authority=compute-proposal` and
  `requires_java_validation=true`; no durable assignment or Java state is
  mutated. Debounce and cooldown enforce bounded trigger frequency.

## Evidence

- Focused tests cover all five trigger kinds, approval metadata and trace,
  before/after metrics, generation, debounce/cooldown sequencing, no-op holds,
  monotonic-time rejection, and invalid policy/metric/trigger contracts.
- `./scripts/compute-api.ps1 -Action check` passes 131 tests at 95.66% coverage,
  Ruff, format, mypy, contract validation, and 5 schemas/15 fixtures.
- `./scripts/full-gate.ps1` passes Java 60 tests, Python 131 tests at 95.66%,
  Web 38 unit tests/build, and 5 schemas/15 fixtures.

## Gate decision

Local L2 replanning and L5 bounded-resilience evidence is complete. Remote
GitHub Actions validation is required before `TASK_GRAPH.yaml` changes RM-135
to `passed`.
