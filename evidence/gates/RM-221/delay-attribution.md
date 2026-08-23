# RM-221 Delay Attribution Accounting Evidence

Date: 2026-08-24
Implementation checkpoint: pending commit
GitHub Actions: pending

## Scope

The Python compute API exposes `POST /api/v1/eta/delay-accounting` with
per-record observed duration, clock domain, and ETA components. It normalizes
dispatch, travel, preparation, pickup, and delivery into a stable order and
returns accounted duration, residual, missing components, clock mismatches, a
record status, and a canonical digest. Aggregate totals reconcile the supplied
records and count reconciled, incomplete, and clock-mismatch records.

Statuses are explicit: `RECONCILED` requires all five components in the same
clock domain and a zero residual; `UNRECONCILED` reports a non-zero residual;
`INCOMPLETE` reports missing components; `CLOCK_DOMAIN_MISMATCH` refuses to
claim a trustworthy residual. The response is labeled accounting decomposition,
not causal inference.

## Local evidence

- `./scripts/compute-api.ps1 check` - PASS, 208 Python tests at 95.29%
  coverage, strict mypy/Ruff/format, 6 schemas, 18 contract fixtures,
  determinism, archive, marts, and semantic-metrics gates.
- `./scripts/full-gate.ps1` - PASS, including Java 80 tests, Compute 208 tests
  at 95.29%, Web 52 unit tests/build, contracts, and repository gates.
- `tests/test_delay_accounting.py` - PASS reconciliation, residual,
  incompleteness, clock mismatch, aggregate totals, duplicate IDs, and input
  validation.
- `tests/test_api.py` - PASS API projection, trace propagation, explicit
  missing-component state, and duplicate rejection.

## Boundary and limitations

This is descriptive accounting only. A residual is not a causal explanation,
and a reconciled sum is not proof that component labels caused the duration.
The implementation does not persist order state; Java remains the durable
business-state owner. Clock-domain checks protect replay/live separation.

## Remote validation

The implementation checkpoint and GitHub Actions run will be recorded here
after the commit is pushed and all required jobs pass.
