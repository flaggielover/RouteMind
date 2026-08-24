# R3-314 Public VRPTW Verifier Evidence

Date: 2026-08-24 (Asia/Shanghai)

Base revision: `c2ac98f7f56019c02224f1948ff1ee59c4ac47b7`

Engineering Gate: E-PASS

Experiment Gate: X-NOT-REQUIRED

Statistical Gate: S-NOT-APPLICABLE

Claim Gate: C-NOT-APPLICABLE

## Scope

- Added explicit untrusted public-solver output contracts for visits, routes, and
  solutions without coupling them to a solver implementation.
- Added a solver-independent Cartesian VRPTW verifier that recomputes route and
  total distance, arrival continuity, service duration, customer coverage,
  capacity, time windows, depot shape, vehicle identity/count, unassigned policy,
  and feasibility-claim consistency.
- Canonical VRPTW v1 has no pickup-delivery relation, so the verifier records
  `precedence_not_applicable_to_canonical_vrptw_v1` rather than claiming that a
  nonexistent constraint was checked.
- Explicit waiting at the depot or a customer remains valid when continuity,
  service duration, and the due time all hold.

## Independence Boundary

`verify_public_vrptw_solution` accepts only a canonical instance and an untrusted
result value. It does not receive a solver, callback, model, or solver-internal
state. Feasibility and objectives are recomputed from the canonical instance.

## Executable Evidence

Directed failure matrix:

```text
F:\Projects\RouteMind\.tools\uv\Scripts\uv.exe run --frozen pytest tests/test_public_verification.py --no-cov -q
................................
32 passed in 0.14s
```

Strict directed static checks:

```text
ruff check ...
All checks passed!
mypy ...
Success: no issues found in 3 source files
```

Full available repository gate:

```text
.\scripts\full-gate.ps1
PASS: task graph schema, dependencies, states, and evidence rules
PASS: Compose configuration
Java: 80 tests, 0 failures, 0 errors
Python: 296 passed; total coverage 95.59% (threshold 95%)
Contracts: 6 schemas and 18 fixtures
Web: 34 test files, 92 tests; production build passed
PASS: RouteMind full available gate
```

## Claim Boundary

This evidence establishes implementation integrity for the independent verifier.
It does not establish solver feasibility rates, optimality, performance, public
benchmark quality, or external validity. Those claims remain gated by later Round
3 experiments and statistical review.

## Remote Evidence

Checkpoint `921a0d0` passed all five jobs in GitHub Actions run `32694841407`:
control plane and Compose, Java, Python and contracts, bounded degradation and
resilience, and Web static/unit/build/browser smoke.
