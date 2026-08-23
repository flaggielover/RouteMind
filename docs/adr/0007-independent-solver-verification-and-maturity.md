# ADR-0007: Independent Solver Verification and Maturity Labels

## Status

Accepted for RM-206.

## Decision

Compute results cross an independent verification boundary before they are
returned to dispatch, experiment, RouteBench, or shadow callers. The verifier
does not call `DispatchProblem.candidate_rejection_reasons` or the VRPTW
planner's private route evaluator. It recomputes candidate constraints and,
for VRPTW plans, route travel, timing, load, availability, return-to-depot,
unassigned coverage, and the aggregate travel objective.

Invalid output raises `SolverOutputInvalidError`. The API maps it to HTTP 503
with `code=solver_output_invalid`, the failed check names, and structured
reason codes. No invalid result is converted into a successful fallback or
silently persisted.

## Maturity classification

These labels describe the registered implementation, not a claim about a
future production system:

| Strategy | Maturity | Supported scope and constraints | Complexity / limitations | Fallback |
| --- | --- | --- | --- | --- |
| nearest | BASELINE | One request; available state, capacity, risk, availability and delivery window | O(n log n), great-circle objective; no network route optimization | Unassigned with explicit reasons |
| weighted-greedy | BASELINE | One request; weighted pickup distance plus the shared dispatch constraints | O(n log n); configuration is local and deterministic | Unassigned with explicit reasons |
| hungarian | BASELINE | One request adapter over a finite candidate set | O(n^3) reference assignment implementation; not a multi-request authority | Unassigned with explicit reasons |
| minimum-cost-flow | ENGINEERING | Bounded batch assignment with capacity and shared dispatch feasibility | Successive shortest augmenting path; no claim of large-scale optimality | Explicit unassigned reasons |
| partitioned-assignment | ENGINEERING | Minimum-cost flow per deterministic zone partition | Inherits flow limits; partition is a bounded heuristic | Explicit unassigned reasons |
| vrptw | BASELINE | Small bounded VRP/VRPTW insertion route; service time, windows, capacity, vehicle availability and optional return | Deterministic greedy insertion, capped at 32 stops/vehicles; not an industrial exact solver | Explicit unassigned reasons or verification failure |

No registered strategy is marked `PRODUCTION-CANDIDATE`, `RESEARCH`, or
`EXTERNAL-VALIDATED` until matching operational or external evidence exists.

## Consequences

The independent kernel adds a deliberate failure boundary and property-style
tests for tampered outputs, constraint violations, route objective drift,
unassigned semantics, and invalid travel-provider results. The verifier is
not a theorem prover; it is an executable consistency and feasibility gate
whose assumptions are recorded by the checks it reports.
