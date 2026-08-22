# RM-085 Staged Release and Rollback Decision Evidence

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: `4367cafc20beff9b5ddb6cd5be3b96b4fa3574c7`
- Worktree: clean after the implementation checkpoint

## Contract and policy

`scripts/staged_release.py` defines immutable content-addressed `StagePlan`,
ordered `ReleaseStage`, `StageObservation`, and `StageDecision` values. Stage
traffic allocations are normalized and strictly increasing to 10,000 basis
points. Evaluation is read-only and deterministic: rollback takes precedence
for unavailable rollback readiness, missing/unhealthy required checks, or an
error/regression/disagreement threshold at or above its configured limit;
otherwise incomplete sample/soak data holds, and only a complete safe stage
promotes to the next declared cohort.

## Commands and results

1. `python scripts/staged_release_test.py` -> 5 tests passed.
2. `python -m py_compile scripts/staged_release.py scripts/staged_release_test.py` -> passed.
3. `./scripts/verify.ps1` -> control-plane, security, recovery, release
   preflight, staged-release, Compose, and PowerShell syntax gates passed.
4. `./scripts/full-gate.ps1` -> Java 34 tests passed; Python 56 tests passed at
   96.05% statement/branch coverage; 4 schemas and 12 fixtures passed; Web
   formatting, lint, typecheck, unit, and production build passed.

The self-tests cover canonical plan digests, threshold boundaries, rollback
precedence over incomplete observations, unknown stages, missing health checks,
and no-write behavior.

## Boundary

This is a local policy evaluator only. Service-mesh traffic shifting, live
monitoring, registry verification, deployment orchestration, and production
rollback execution remain external gates and are not claimed.
