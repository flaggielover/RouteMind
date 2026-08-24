# R3-347 Counterfactual Decision X-Ray Support Audit

Date: 2026-08-25 (Asia/Shanghai)
Status: closed as a read-only `INSUFFICIENT_DATA` support audit
Implementation: `09d4194d2093af0a6752ad9ba22f6e3877da7fba`
GitHub Actions: PASS - run `32785397588` (all five jobs)

## Frozen replay boundary

Manifest:
`docs/research/r3/manifests/rads/r3-347-counterfactual-xray-v1.json`

- Plan digest:
  `4c76ce8200f00adeeb2690051d7615fa47d710523b78d631e849385b135047ce`
- Byte SHA-256:
  `d7306891950446216d4188a672a0ebfd6d5154b76555d65208b4d12f2a261f90`
- Required outputs retain original decision, bounded perturbation,
  counterfactual decision, same-unit objective/risk deltas, minimality
  verification, and exact replay lineage.
- Required lineage keeps source decision/state, strategy/version, reference
  data, and replay digests under the same model and reference data.
- Minimality uses bounded L0 then L1 lexicographic search when computed.
- Output is always a model/system counterfactual replay, never causal inference
  or a production effect.

## Read-only source audit

The R3-350 corpus and RM-226 Decision X-Ray boundary were inspected after the
frozen implementation passed remote CI. The corpus has two summary records and
the X-Ray provides read-only explanation plus captured-snapshot digest
comparison. They do not provide an executable perturbation engine.

Formal audit digest:
`9c4be0fd4c7d2f7b54e1ccc92fd34ef84e7bb37e6f4a2e1ccc488673996107d8`.

The audit returned:

- status: `INSUFFICIENT_DATA`
- source record count: `2`
- replay count: `0`
- available field: `original_decision_summary`
- missing fields: `captured_feature_state`, `executable_policy_bundle`,
  `perturbation_values`, `counterfactual_decision_output`,
  `objective_before_after`, `risk_before_after`, `replay_identity`, and
  `minimality_evidence`
- all six dimensions: `NOT_PERTURBED_NO_EXECUTABLE_REPLAY`
- all seven outputs: `NOT_REPORTED_INSUFFICIENT_REPLAY_SUPPORT`
- deltas: `NOT_COMPUTED_NO_COUNTERFACTUAL_OUTPUT`
- minimality: `NOT_VERIFIED_NO_EXECUTABLE_REPLAY`
- lineage: `SOURCE_SUMMARY_ONLY_NO_REPLAY_LINEAGE`

No perturbation, new decision, objective/risk delta, minimality search, external
write, or causal interpretation was produced. Running the generic What-if
engine would create a different experiment and was not used to fill missing
Decision Corpus evidence.

## Executable evidence

- Eight directed tests reach 100% module statement and branch coverage across
  current insufficiency, complete support, missing replay, malformed counts,
  and all plan/policy/lineage/execution drift.
- `./scripts/full-gate.ps1`: PASS - Java 81/81, Python 920/920 at 95.11%, Web
  92/92 plus production build, and all repository controls.
- Actions run `32785397588`: all five jobs passed for implementation SHA
  `09d4194d2093af0a6752ad9ba22f6e3877da7fba` before the formal audit.

## Final disposition

R3-347 closes `E-PASS / X-PASS / S-NOT-APPLICABLE / C-NO-CLAIM`.
The replay protocol is executable, but the retained corpus cannot support a
counterfactual replay. R3-325 remains frozen exactly as
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM` and was not rerun.
