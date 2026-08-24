# R3-317 Solver Outcome and Resource Semantics Evidence

Date: 2026-08-24 (Asia/Shanghai)

Base revision: `2d6eb08f18ca28b55b9185e8573d1796c6aae13a`

Engineering Gate: E-PASS

Experiment Gate: X-PASS (frozen contract-matrix replay only)

Statistical Gate: S-NOT-APPLICABLE

Claim Gate: C-NOT-APPLICABLE

## Contract

- `OPTIMAL`, `FEASIBLE_INCUMBENT`, `INFEASIBLE_PROVEN`,
  `TIMEOUT_WITH_FEASIBLE`, `TIMEOUT_NO_FEASIBLE`,
  `RESOURCE_LIMIT_WITH_FEASIBLE`, `RESOURCE_LIMIT_NO_FEASIBLE`, and `FAILED`
  are distinct terminal outcomes.
- Termination, proof, incumbent presence, independent verification, configured
  limits, and measured usage remain independent typed dimensions.
- Error/cancellation takes precedence over retained output. Wall-time breach takes
  precedence over other resource breaches. No limit outcome can become exact.
- Only an independently verified complete incumbent is accepted as feasible.
  Partial, rejected, absent, and unverified outputs remain outside the feasible
  completion numerator.
- The resource-limit object is immutable and digestible. Independently observed
  usage over a frozen limit overrides a solver's reported `COMPLETED` termination.

The frozen semantics are documented in
`docs/research/r3/SOLVER_OUTCOME_CONTRACT.md`.

## Frozen Matrix

Manifest:
`docs/research/r3/manifests/solver-outcomes/solver-outcome-matrix-v1.json`

SHA-256:
`4ab08b71cdcc15ba2203bd6761bf9dc8cebe95f1b4191b51700dd7ecd0383262`

The manifest contains 17 non-cherry-picked combinations and covers all eight
terminal outcomes. It exercises optimal/feasible/infeasible proof semantics,
reported and observed timeout/memory/node limits, every verification disposition,
error with retained verified output, cancellation, and completed-without-output.

## Executable Evidence

Directed contract and matrix replay:

```text
pytest tests/test_solver_outcomes.py --no-cov -q
..........................................
42 passed in 0.21s
```

Strict directed static checks:

```text
ruff check ...
All checks passed!
mypy ...
Success: no issues found in 2 source files
```

Full available repository gate:

```text
.\scripts\full-gate.ps1
PASS: task graph schema, dependencies, states, and evidence rules
PASS: Compose configuration
Java: 80 tests, 0 failures, 0 errors
Python: 338 passed; solver_outcomes.py 100%; total coverage 95.74%
Contracts: 6 schemas and 18 fixtures
Web: 34 test files, 92 tests; production build passed
PASS: RouteMind full available gate
```

## Evidence Boundary

The frozen matrix is a contract experiment, not a solver or public benchmark
experiment. It establishes reproducible classification semantics only. It provides
no empirical scale, timeout rate, solver feasibility, objective quality,
optimality, or external-validity claim. Those remain gated by R3-311/R3-312 and
later statistical/reproduction tasks.

## Remote Evidence

Checkpoint `c05d482` passed all five jobs in GitHub Actions run `32695879055`:
control plane and Compose, Java, Python and contracts, bounded degradation and
resilience, and Web static/unit/build/browser smoke. The Python job replayed the
same frozen matrix on Linux.
