# RM-219 Honest ETA Foundation Evidence

Date: 2026-08-24
Implementation checkpoint: pending
GitHub Actions: pending

## Scope

The Python compute API exposes `/api/v1/eta/predict` using a deterministic
baseline. It composes five components: dispatch wait, travel (courier to
pickup plus pickup to delivery), merchant preparation, pickup service, and
delivery service. The response carries prediction time, horizon, model/version,
canonical input digest, predicted delivery time, and optional actual outcome
duration.

Preparation is required for a predicted delivery timestamp. When unavailable,
the preparation component is explicitly unavailable and no fabricated ETA is
returned. The response is labeled `deterministic baseline; not calibrated
production accuracy`.

## Local evidence

- `./scripts/compute-api.ps1 check` - PASS, 196 Python tests at 95.30% coverage,
  strict mypy/Ruff/format, 6 schemas, 18 fixtures, determinism, archive, marts,
  and semantic metrics gates.
- `./scripts/full-gate.ps1` - PASS after implementation integration, including
  Java 80 tests, Compute 196 tests at 95.30%, Web 52 unit/build, contracts, and
  repository gates.
- `tests/test_eta.py` - PASS component composition, missing-input behavior,
  outcome duration, digest, and model/contract validation.
- `tests/test_api.py` - PASS trace propagation, five-component response,
  optional outcome, and explicit unavailable preparation behavior.

## Boundary and limitations

No calibration, MAE, quantile coverage, SLA confidence, or AI accuracy is
claimed. No Java order state or durable business record is mutated by this
read-oriented baseline endpoint. RM-220 owns calibration and risk thresholds.

Remote Actions evidence remains pending until this checkpoint is pushed.
