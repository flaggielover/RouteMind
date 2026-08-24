# R3-334 Twin Calibration Drift

Date: 2026-08-25 (Asia/Shanghai)
Status: passed with the predeclared no-data outcome
Implementation checkpoint: `46b179c34d42d6405a539ccce6c33958344dd0e4`
GitHub Actions: PASS - run `32749546141` (all five jobs)

## Frozen drift plan

The machine-readable plan is
`docs/research/r3/manifests/twin/r3-334-calibration-drift-v1.json`.
Its canonical plan digest is
`587d71667062561ee98c4fe17434178dead070df30b4f1b7e33538d3bb7c3478` and its
byte SHA-256 is
`c9c85367985a04a7cd965448a23781f097eea58e7fc2905c7063d302ffc6aa14`.

The plan freezes four regime axes in order: `time`, `zone`, `demand`, and
`traffic`. It keeps parameter drift separate from fidelity degradation:
parameter metrics are `parameter_l1_delta` and `parameter_relative_delta` with
mandatory before/after checksums; fidelity metrics are the four R3-333 protocol
identities against the frozen protocol baseline. Unsupported regimes must
remain `NOT_ANALYZED_NO_DATA`. Synthetic data is forbidden, and a recalibration
script is explicitly not considered a solved auto-calibration system.

## Executed outcome

The report loaded the R3-330 split contract and R3-332 held-out outcome before
checking support. Both authorized split artifacts are
`UNAVAILABLE_NO_OBSERVED_DATA` with zero records. The report therefore returned:

- overall status: `INSUFFICIENT_DATA`;
- parameter drift: `NOT_ANALYZED_NO_DATA`;
- fidelity degradation: `NOT_ANALYZED_NO_DATA`;
- `time`, `zone`, `demand`, `traffic`: each `NOT_ANALYZED_NO_DATA`, record count
  `0`, with both separated paths `NOT_ANALYZED_NO_DATA`.

No parameter delta, fidelity degradation estimate, unsupported-regime
imputation, synthetic replay, or stability/external-validity claim was
produced. The absence of data remains explicit rather than being masked by a
single recalibration script.

## Executable evidence

- `tests/test_twin_drift.py`: six directed tests; the drift module reaches 100%
  statement and branch coverage.
- `./scripts/compute-api.ps1 -Action check`: PASS - 820/820 Python tests,
  95.57% total coverage, 143 files checked by Ruff/mypy, 6 schemas/18 fixtures,
  determinism, analytical archive/mart, and semantic metrics.
- GitHub Actions run `32749546141`: PASS for Java, Python/contracts,
  Web/browser smoke, control-plane/Compose, and bounded degradation/resilience.

## Final disposition

R3-334 closes `E-PASS / X-PASS / S-NOT-APPLICABLE / C-NO-CLAIM`. The
`INSUFFICIENT_DATA` and per-regime `NOT_ANALYZED_NO_DATA` results are valid
scientific boundary evidence, not a stability or external-validity claim.
