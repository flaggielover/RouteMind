# R3-348 Preregistered RADS Ablation Support Audit

Date: 2026-08-25 (Asia/Shanghai)
Status: closed as a read-only `INSUFFICIENT_DATA` support audit
Implementation checkpoint: `771e8a81c819c2006473fa6a0a55fef5bcfc7fe6`
GitHub Actions: PASS - run `32774570495` (all five jobs)

## Frozen ablation boundary

Manifest: `docs/research/r3/manifests/rads/r3-348-rads-ablation-v1.json`

- Canonical digest:
  `c5644b75580db5d95f33a28ea6cd367906a235aac777f46890f862cdf952d2e7`
- Byte SHA-256:
  `388598f7c0265ecfad9f99247b6efc8124b8bc53383d49d102f4be269879d2b4`
- Preregistered dimensions: risk, adaptation, hysteresis, uncertainty,
  counterfactual feature, and threshold.
- The counterfactual-feature ablation is
  `NOT_APPLICABLE_FEATURE_ABSENT` because the frozen RADS stack has no such
  feature. It is retained in the matrix rather than silently omitted.
- Applicable dimensions use paired seed/regime/stream units, paired
  differences, 95% uncertainty, at least 30 pairs, and Holm correction across
  the applicable dimension-metric family.
- Any component removal chosen after results is `EXPLORATORY_ONLY`; changing
  the frozen matrix requires a new manifest version.

## Read-only support audit

R3-325 remains exactly frozen at
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`. Its immutable artifacts contain
aggregate paired arm summaries but none of the six fields required to evaluate
component-level ablations:

- `common_stream_identity`
- `decision_outcomes`
- `switching_observations`
- `constraint_outcomes`
- `uncertainty_calibration`
- `threshold_sensitivity_runs`

The audit returned `INSUFFICIENT_DATA`. Risk, adaptation, hysteresis,
uncertainty, and threshold are `NOT_EVALUATED_NO_ABLATION_LOGS`; the
counterfactual-feature dimension remains `NOT_APPLICABLE_FEATURE_ABSENT`.
All eight metrics are `NOT_REPORTED_NO_ABLATION_LOGS`. No material campaign,
R3-325 rerun, synthetic substitution, external write, component-importance
estimate, multiplicity result, or scientific effect claim was produced.

## Executable evidence

- Targeted R3-348 tests: 6/6 passed, covering the complete/missing support
  branches and rejection of digest, identity, dimension, analysis, support,
  lineage, execution-policy, and exploratory-boundary drift.
- `./scripts/full-gate.ps1`: PASS - Java 81/81, Python 881/881 at 95.43%
  total coverage, Web 92/92 plus production build, Ruff, formatting, strict
  mypy, six schemas/18 fixtures, determinism, analytics, semantic metrics,
  repository controls, and bounded resilience.
- GitHub Actions run `32774570495`: all five jobs passed for implementation
  SHA `771e8a81c819c2006473fa6a0a55fef5bcfc7fe6`.

## Final disposition

R3-348 closes `E-PASS / X-PASS / S-NOT-APPLICABLE / C-NO-CLAIM`.
The frozen design is reproducible, but current evidence cannot estimate any
applicable component effect or importance.
