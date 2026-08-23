# RM-207 Determinism Audit Evidence

## Contract

`services/compute-api/src/routemind_compute/application/determinism.py`
defines `DETERMINISM_CRITICAL`, `DETERMINISTIC_IF_CONFIGURED`, and
`NONDETERMINISTIC_ALLOWED` contracts. `audit_scenario` executes a seeded
canonical scenario twice, normalizes configuration, records Python/platform/
hash-seed environment metadata, compares replay digests, and raises
`DeterminismViolationError` for the first two classifications on drift.

The operational UUID and wall-clock response paths are explicitly allowed
nondeterminism and are excluded from replay digests.

## Gate

`scripts/compute-api.ps1 -Action check` now runs
`scripts/determinism_gate.py` after the frozen Python tests. The gate's local
canonical run reported equal digests:

```text
seed=20260823
subsystem=scenario-kernel
first_digest=a6ca7255cf1c1486861107a1cc25d17117a9e75f19a42920069275cb956a0993
second_digest=a6ca7255cf1c1486861107a1cc25d17117a9e75f19a42920069275cb956a0993
stable=true
```

## Executed evidence

```text
.\scripts\compute-api.ps1 -Action check
```

Result: Ruff, formatting, mypy, contract validation, determinism gate, and
160 Python tests passed. Coverage is 95.84% (threshold 95%). Focused
determinism tests: 5 passed. GitHub Actions run 32629142871 passed all five
jobs.

## Limits

This is a reproducibility gate for declared contracts, not a claim that every
operational identifier or external provider is bitwise deterministic. External
travel data, hardware and provider versions must be recorded by their own
provenance boundary before cross-environment claims are made.
