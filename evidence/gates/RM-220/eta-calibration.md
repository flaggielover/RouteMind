# RM-220 ETA Calibration and SLA Risk Evidence

Date: 2026-08-24
Implementation checkpoint: 7f7af74
GitHub Actions: PASS - run 32652719384 (all five jobs)

## Scope

The Python compute API exposes `POST /api/v1/eta/calibration`. It accepts
explicit prediction/outcome samples, calculates MAE, median absolute error,
interpolated p90 error, and interval coverage, and returns a stable digest.
Duplicate sample IDs, incomplete intervals, invalid durations, and invalid SLA
budgets are rejected. The response classifies SLA exposure as `ON_TRACK`,
`AT_RISK`, or `LIKELY_LATE` using deterministic thresholds.

Calibration is evidence-gated: an empty sample set returns `UNAVAILABLE`, all
metrics remain null, and `customer_confidence` is `unavailable`. A populated
sample set may report `available` confidence only as a calibration-evidence
state. The response label explicitly says it is not a customer guarantee.

## Local evidence

- `./scripts/compute-api.ps1 check` - PASS, 201 Python tests at 95.23%
  coverage, strict mypy/Ruff/format, 6 schemas, 18 contract fixtures,
  determinism, archive, marts, and semantic-metrics gates.
- `./scripts/full-gate.ps1` - PASS, including Java 80 tests, Compute 201 tests
  at 95.23%, Web 52 unit tests/build, contracts, and repository gates.
- `tests/test_eta_calibration.py` - PASS metrics, interval coverage, explicit
  unavailable state, SLA thresholds, duplicate and interval validation.
- `tests/test_api.py` - PASS populated calibration response, trace propagation,
  and confidence gating when outcomes are absent.

## Boundary and limitations

The implementation does not claim production calibration quality, causal delay
explanations, or probabilistic customer guarantees. Samples are supplied by a
caller and are not persisted as Java order state. RM-221 owns descriptive delay
accounting; later research tasks must supply stronger data lineage before any
customer-facing accuracy claim.

## Remote validation

GitHub Actions run `32652719384` passed the Java, control-plane/Compose,
Python/contracts, Web static/unit/browser, and bounded degradation/resilience
jobs for checkpoint `7f7af74`.
