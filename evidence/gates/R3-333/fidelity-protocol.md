# R3-333 Preregistered Twin Fidelity Protocol

Date: 2026-08-24 (Asia/Shanghai)
Status: passed
Implementation checkpoint: `c0283c74e2cc9ad9e9703adc60bfe1097835e421`
GitHub Actions: PASS - run `32744065301` (all five jobs)

## Frozen metrics and thresholds

The machine-readable protocol is
`docs/research/r3/manifests/twin/r3-333-fidelity-protocol-v1.json`.
Its canonical protocol digest is
`de453fdf1181b2e5a52839eb9f1b7536db3f5f5fb1177f4b5351269cfa3c1825` and its
byte SHA-256 is
`a3007f1ca9892fd0b7746797e53dec9ab5aecc5e243d188b16f12564df2ea8ff`.

Four variable-appropriate metrics are frozen in this order:

- `assignment_rate`: mean absolute error in proportion, threshold `0.05`;
- `scenario_risk_index`: mean absolute error on a bounded `[0,1]` index,
  threshold `0.05`;
- `dispatch_latency_seconds`: p90 absolute error in seconds, threshold `30.0`;
- `fallback_rate`: mean absolute error in proportion, threshold `0.02`.

Every metric requires at least 100 calibration and 100 held-out records. Every
metric also uses the fixed paired absolute-error delta against the
`naive_uncalibrated_baseline`, alpha `0.05`, with improvement only supported
when the upper two-sided 95% interval is below the frozen zero effect. No
threshold, metric, baseline, alpha, or support rule may be changed after
held-out outcomes are inspected.

## Missing-data behavior and claim boundary

The support gate is executable and read-only. Empty or sub-threshold held-out
support returns `INSUFFICIENT_DATA` with the missing metric identities; complete
support only returns `READY_FOR_VALIDATION` and does not estimate a metric or
effect. The protocol claim boundary is
`FIDELITY_PROTOCOL_DOES_NOT_ESTABLISH_TWIN_VALIDITY`.

R3-330 currently reports no authorized observed outcomes, so R3-331 calibration
and R3-332 held-out validation remain unexecuted. Synthetic Twin replay is not
used to satisfy the support gate, and no fidelity or external-validity claim is
promoted.

## Executable evidence

- `tests/test_twin_fidelity_protocol.py`: 12 directed tests; loader reaches
  100% statement and branch coverage, including digest, identity, metric order,
  thresholds, improvement policy, support policy, and missing-data behavior.
- `./scripts/compute-api.ps1 -Action check`: PASS - 798/798 Python tests,
  95.32% total coverage, Ruff, strict mypy, 6 schemas/18 fixtures,
  determinism, analytical archive/mart, and semantic metrics.
- GitHub Actions run `32744065301`: PASS for Java, Python/contracts,
  Web/browser smoke, control-plane/Compose, and bounded degradation/resilience.

## Final disposition

R3-333 closes `E-PASS / X-NOT-REQUIRED / S-NOT-APPLICABLE /
C-NOT-APPLICABLE`. This is a preregistration engineering result, not observed
Twin fidelity evidence.
