# Round 3 Scientific Control Plane Design

## Decision

Make `TASK_GRAPH.yaml` the executable source for Round 3 and retain
`docs/research/ROUND_3_TASK_GRAPH.yaml` as its scientific index and historical
reclassification record. Research tasks carry orthogonal E/X/S/C status, while
the existing generic status continues to drive dependency selection and recovery.

## Boundaries

The graph has five workstreams: external validity/solver science, Statistical
RouteBench, Digital Twin science, RADS research, and advanced evaluation/closure.
Production identity, preferences/notifications, production readiness, telemetry
productization, and broad agent evaluation are preserved for Round 4 or a
non-blocking parallel lane. The Java/Python/data-root ownership model is unchanged.

## Control behavior

`scripts/validate_control_plane.py` requires classification, workstream, and valid
E/X/S/C status for every `R3-*` task. A research task cannot be generically passed
with an unfinished experimental, statistical, or claim gate. `scripts/resume.ps1`
prints the four dimensions for the active research task. Validator self-tests
cover a valid scientific task, a missing dimension, and a false passed task.

## Scientific contract

The Research Contract freezes questions, null/alternative hypotheses, initial
effect/non-inferiority gates, data-split rules, manifest fields, exclusions,
stopping, resource limits, and non-claims before experiments. The Claim Matrix
contains every candidate claim and initially permits no final claim. The Negative
Results ledger starts with known evidence limits and is append-only.

## Verification

The fast repository gate validates graph structure, validator self-tests,
security/recovery/release controls, Compose syntax, and PowerShell syntax. GitHub
CI verifies engineering integrity only. R3-300 cannot create X/S/C evidence and is
therefore `X-NOT-REQUIRED`, `S-NOT-APPLICABLE`, and `C-NOT-APPLICABLE`.
