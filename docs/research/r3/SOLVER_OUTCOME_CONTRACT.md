# Solver Outcome, Timeout, and Incumbent Contract

Contract version: `solver-outcome-contract-v1`

Frozen: 2026-08-24 (Asia/Shanghai), before material public benchmark execution

## Independent Dimensions

A public solver adapter must report these dimensions independently:

- termination: completed, wall-time limit, memory limit, search-node limit,
  cancellation, or error;
- proof: none, optimality, or infeasibility;
- incumbent: absent or present;
- independent verification: not run, rejected, verified partial, or verified
  complete;
- configured limits: wall time, optional memory, optional search nodes, threads;
- observed usage: elapsed time, optional peak memory, optional explored nodes.

Solver text such as `feasible`, `success`, or `optimal` is not itself an outcome.
It becomes evidence only after typed adaptation and independent verification.

## Outcome Precedence

Classification is deterministic and fail-closed:

1. Error or cancellation is `FAILED`, even if diagnostic output contains a
   verified route. The verified fact is retained but the incumbent is not accepted.
2. A reported or independently observed wall-time breach is
   `TIMEOUT_WITH_FEASIBLE` only for a verified complete incumbent; otherwise it is
   `TIMEOUT_NO_FEASIBLE`.
3. A memory or node breach is `RESOURCE_LIMIT_WITH_FEASIBLE` only for a verified
   complete incumbent; otherwise it is `RESOURCE_LIMIT_NO_FEASIBLE`.
4. `INFEASIBLE_PROVEN` requires completed termination, a typed infeasibility proof,
   and no incumbent.
5. `OPTIMAL` requires completed termination, a typed optimality proof, no observed
   resource breach, and a verified complete incumbent.
6. A completed verified complete incumbent without proof is
   `FEASIBLE_INCUMBENT`.
7. Every remaining combination is `FAILED`.

Timeout, infeasibility, failure, and resource exhaustion are never denominated as
ordinary success. `TIMEOUT_WITH_FEASIBLE` preserves a useful incumbent without
claiming exactness. A partial or unverified solution never counts as feasible for
the complete-solution benchmark metric.

## Resource Semantics

The limits object is immutable and digestible. Adapters must preserve its digest
with each run. A solver-reported `COMPLETED` status cannot hide observed usage over
the frozen wall-time, memory, or search-node limit. Conversely, an explicit limit
termination remains a limit outcome even when sampled usage is just below the
configured boundary.

Resource monitoring resolution and enforcement mechanism are adapter/environment
metadata for later R3-311/R3-312 manifests. This contract does not claim hard OS
isolation or measured solver scale.

## Claim Boundary

The contract permits truthful counting and later experiment design. It provides no
solver feasibility, optimality, quality, runtime, scale, or external-validity
evidence by itself. Those gates require manifest-bound public benchmark runs and
independent reproduction.
