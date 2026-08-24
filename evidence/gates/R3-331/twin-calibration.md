# R3-331 Bounded Twin Calibration

Date: 2026-08-24 (Asia/Shanghai)
Status: passed with the predeclared no-data outcome
Implementation checkpoint: `e5dce058db948d78cfacb4179f4b87cf52a2b4a5`
GitHub Actions: PASS - run `32746310588` (all five jobs)

## Frozen calibration plan

The machine-readable plan is
`docs/research/r3/manifests/twin/r3-331-calibration-plan-v1.json`.
Its canonical plan digest is
`86f17d2edb74a25a806348461917c9943fa9cb765579c01becccb82def02937f` and its
byte SHA-256 is
`949c4d9c82a0af60e5d0bfab17d78bd5700f73a565ffd5f3954ab6816f89e208`.

The plan binds four identifiable targets to the R3-333 metric identities:
`assignment_rate`, `scenario_risk_index`, `dispatch_latency_seconds`, and
`fallback_rate`. It freezes a weighted calibration-split mean-absolute-error
objective, lower-is-better direction, four finite parameter bounds, frozen
baseline initialization, bounded coordinate descent, seed `331`, 50 maximum
iterations, tolerance `0.0001`, five no-improvement stopping iterations, and
L2 regularization with lambda `0.01`.

Calibration and held-out split IDs are copied from the R3-330 contract. The
plan rejects held-out reads, requires observed calibration data, and requires
SHA-256 checksums for before-parameters, after-parameters, and the calibration
artifact whenever a fit can run. The claim boundary is
`CALIBRATION_FIT_DOES_NOT_ESTABLISH_TWIN_VALIDITY`.

## Executed outcome

The runner loaded and validated the R3-330 split contract and R3-333 fidelity
protocol before inspecting support. The authorized calibration split has zero
observed records and status `UNAVAILABLE_NO_OBSERVED_DATA`; the held-out split
also has zero records. The runner therefore returned:

- status: `INSUFFICIENT_DATA`;
- missing targets: all four frozen metric identities;
- calibration records: `0`;
- held-out records: `0`;
- parameter-before SHA-256: `None`;
- parameter-after SHA-256: `None`;
- fitted-artifact SHA-256: `None`.

No optimization, parameter fitting, checksum fabrication, held-out read, or
synthetic Twin replay occurred. Manifest counts cannot produce a calibration
fit; a future data-backed implementation requires a separately reviewed path.
This outcome is valid terminal evidence for the current data boundary and does
not establish Twin fidelity or external validity.

## Executable evidence

- `tests/test_twin_calibration.py`: nine directed tests; the calibration module
  reaches 100% statement and branch coverage.
- `./scripts/compute-api.ps1 -Action check`: PASS - 807/807 Python tests,
  95.42% total coverage, 139 files checked by Ruff/mypy, 6 schemas/18 fixtures,
  determinism, analytical archive/mart, and semantic metrics.
- GitHub Actions run `32746310588`: PASS for Java, Python/contracts,
  Web/browser smoke, control-plane/Compose, and bounded degradation/resilience.

## Final disposition

R3-331 closes `E-PASS / X-PASS / S-NOT-APPLICABLE / C-NO-CLAIM`. The
`INSUFFICIENT_DATA` result is retained as scientific boundary evidence; it is
not a failed implementation and does not authorize a Twin-validity claim.
