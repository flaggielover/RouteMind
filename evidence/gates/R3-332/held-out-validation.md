# R3-332 Held-Out Twin Validation

Date: 2026-08-24 (Asia/Shanghai)
Status: passed with the predeclared no-data outcome
Implementation checkpoint: `311d7a09136a91962f0583980eb86a0df625c29c`
GitHub Actions: PASS - run `32748083203` (all five jobs)

## Frozen validation plan

The machine-readable plan is
`docs/research/r3/manifests/twin/r3-332-held-out-validation-v1.json`.
Its canonical plan digest is
`348150cc5bd4bd6dea1261a81e13e7240606bb24cbc1898504ec34d4c8d9cfee` and its
byte SHA-256 is
`3f27f1a35f074ace24a215abd9c70875d2c67267ca70266737ba6f32455eb14c`.

The plan is lineage-bound to the R3-331 calibration plan digest
`86f17d2edb74a25a806348461917c9943fa9cb765579c01becccb82def02937f`, the
R3-330 split contract digest
`fb3f3162ac073815cba838f3fde5a3b8ac94604e21dc4f9049bdf3785d108eaa`, and the
R3-333 fidelity protocol digest
`de453fdf1181b2e5a52839eb9f1b7536db3f5f5fb1177f4b5351269cfa3c1825`.
It freezes the four metric identities, paired bootstrap percentile uncertainty
at confidence `0.95`, minimum 100 observed pairs, and
`NOT_REPORTED_NO_DATA` when support is missing. The held-out split is read-only;
retuning on held-out records is prohibited. Allowed outcomes are exactly
`VALIDATED_FOR_SCOPE`, `PARTIALLY_VALIDATED`, `FAILED_VALIDATION`, and
`INSUFFICIENT_DATA`.

## Executed outcome

The validation gate loaded and checked the frozen R3-331 calibration outcome,
R3-330 split contract, and R3-333 protocol before evaluating held-out support.
The authorized held-out split has zero observed records and status
`UNAVAILABLE_NO_OBSERVED_DATA`. The gate therefore returned:

- outcome: `INSUFFICIENT_DATA`;
- held-out records: `0`;
- `assignment_rate`: `NOT_REPORTED_NO_DATA`, estimate `None`, uncertainty `None`;
- `scenario_risk_index`: `NOT_REPORTED_NO_DATA`, estimate `None`, uncertainty `None`;
- `dispatch_latency_seconds`: `NOT_REPORTED_NO_DATA`, estimate `None`, uncertainty `None`;
- `fallback_rate`: `NOT_REPORTED_NO_DATA`, estimate `None`, uncertainty `None`.

No held-out metric, confidence interval, improvement effect, retuning step,
synthetic replay, or external-validity claim was produced. The calibration
outcome was already frozen as `INSUFFICIENT_DATA`, so validation did not invent
parameters or treat missing artifacts as a failure of implementation.

## Executable evidence

- `tests/test_twin_held_out_validation.py`: seven directed tests; the validation
  module reaches 100% statement and branch coverage.
- `./scripts/compute-api.ps1 -Action check`: PASS - 814/814 Python tests,
  95.50% total coverage, 141 files checked by Ruff/mypy, 6 schemas/18 fixtures,
  determinism, analytical archive/mart, and semantic metrics.
- GitHub Actions run `32748083203`: PASS for Java, Python/contracts,
  Web/browser smoke, control-plane/Compose, and bounded degradation/resilience.

## Final disposition

R3-332 closes `E-PASS / X-PASS / S-NOT-APPLICABLE / C-NO-CLAIM`. The
`INSUFFICIENT_DATA` result is valid scientific boundary evidence; it does not
establish Twin fidelity, external validity, or causal performance.
