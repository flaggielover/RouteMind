# R3-342 RADS-H Hysteresis Experiment Support Audit

Date: 2026-08-25 (Asia/Shanghai)
Status: closed as a read-only `INSUFFICIENT_DATA` support audit
Implementation checkpoint: `d82138b394e7ab0832acb85a6575931054eff48c`
GitHub Actions: PASS - run `32758618433` (all five jobs)

## Frozen experiment boundary

The content-addressed plan is
`docs/research/r3/manifests/rads/r3-342-rads-h-experiment-v1.json`.
Its canonical plan digest is
`725bce8111db8652c6b52ef1c71e63429594aa4a329e0372e524471ea41ac967` and
its byte SHA-256 is
`62eab0fca0a28a758ae6299a83c900752044f3c155f84245e09dadc6e7ac921d`.
The frozen arms are no-hysteresis, fixed, RADS baseline, cooldown, and RADS-H.
The preregistered thresholds are a 25% switching-reduction target, service
non-inferiority margin `-0.02`, route-cost relative bound `+0.03`, and a
Holm family size of 16.

## Read-only support audit

R3-325 remains exactly frozen at `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.
Its retained pair artifacts contain arm-level summaries, assignment/risk/runtime
fields, event identifiers, and stream digests, but not the tick-level evidence
required to execute this experiment. The audit therefore inspected the six
required support fields without rerunning, tuning, reinterpreting, or writing
external R3-325 artifacts:

- `tick_level_strategy_sequence`: missing
- `switch_events`: missing
- `dwell_observations`: missing
- `service_outcomes`: missing
- `latency_observations`: missing
- `recovery_windows`: missing

The report generator returned `INSUFFICIENT_DATA`; all seven metrics
(`switching_rate`, `dwell_ticks`, `service_metric`, `route_cost`,
`dispatch_latency`, `instability`, `recovery`) are
`NOT_REPORTED_NO_SWITCH_LOGS`. Synthetic replay and material external writes
are explicitly forbidden by the plan. No switching, service, cost, latency,
stability, recovery, non-inferiority, multiplicity, or superiority claim is
made. This is a valid scientific no-claim boundary, not an implementation
failure.

## Executable evidence

- `./scripts/compute-api.ps1 -Action check`: PASS - 854/854 Python tests,
  95.77% total coverage, Ruff, strict mypy, schemas/contracts, determinism,
  analytics, semantic metrics, and repository controls.
- Targeted R3-342 tests: 8/8 passed; the loader rejects digest, identity,
  threshold, lineage, and unsafe execution-policy drift; the audit covers both
  the missing-support and all-support branches.
- The local read-only invocation recorded the plan digest and byte SHA above,
  with zero available support fields and all six fields missing.
- GitHub Actions run `32758618433`: PASS for Java, Python/contracts,
  Web/browser smoke, control-plane/Compose, and bounded degradation/resilience.

## Final disposition

R3-342 closes `E-PASS / X-PASS / S-NOT-APPLICABLE / C-NO-CLAIM`.
The experiment remains preregistered for a future authorized dataset that
contains the required tick-level logs; this checkpoint does not authorize or
claim that material campaign.
