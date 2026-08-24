# R3-345 Safe-RADS Experiment Support Audit

Date: 2026-08-25 (Asia/Shanghai)
Status: closed as a read-only `INSUFFICIENT_DATA` support audit
Implementation checkpoint: `bdb6967` (remote CI observed as run `32761030125`)

## Frozen experiment boundary

Manifest: `docs/research/r3/manifests/rads/r3-345-safe-rads-experiment-v1.json`

- Canonical digest: `182a3e6217f2c8e918049a4d55b78e340c8882a58e5dad106a7f738c3433783c`
- Byte SHA-256: `74d83b8fc695e623d6b1a89466f3836bcf6dec618745080920df8080dbb68288`
- Arms: unconstrained, fixed, penalty-only, and conservative.
- Required metrics: violation, feasibility, route cost, lateness, calibration,
  fallback rate, and tightness sensitivity.

## Read-only support audit

R3-325 remains exactly frozen at `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.
Its retained pair artifacts contain arm summaries but none of the six
Safe-RADS evidence fields required for a material campaign:

- `violation_events`
- `feasibility_outcomes`
- `route_cost_observations`
- `lateness_observations`
- `calibration_records`
- `tightness_sensitivity_runs`

The report generator returns `INSUFFICIENT_DATA`; all seven metrics are
`NOT_REPORTED_NO_SAFE_OUTCOMES`. No material run, synthetic replay, external
write, safety wording, violation estimate, feasibility result, calibration
claim, or efficiency claim is produced. This preserves the distinction between
a frozen experiment contract and an evidence-bearing Safe-RADS result.

## Executable evidence

- Targeted R3-345 tests: 6/6 passed, including complete/missing support audit,
  digest and shape rejection, arm/metric/threshold/lineage drift, and unsafe
  rerun policy rejection.
- `./scripts/compute-api.ps1 -Action check`: PASS - 866/866 Python tests,
  95.60% total coverage, Ruff, strict mypy, schemas/contracts, determinism,
  analytics, semantic metrics, and repository controls.
- GitHub Actions run `32761030125`: all five jobs passed (Java,
  Python/contracts, Web/browser smoke, control-plane/Compose, bounded
  degradation/resilience).

## Final disposition

R3-345 closes `E-PASS / X-PASS / S-NOT-APPLICABLE / C-NO-CLAIM`.
The preregistered material campaign remains unauthorized until a dataset with
the six required Safe-RADS outcome fields exists.
