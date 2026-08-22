# P9 RADS Research Baseline

## Goal

Implement a deterministic, research-only Risk-Aware Dispatch Selector (RADS)
that can be measured against the registered dispatch baselines. RADS must
expose its encoded state, risk terms, objective breakdown, and explanation so
experiments are inspectable rather than opaque. It remains in the Python
research/application boundary and is never required for Java business state or
hard real-time dispatch correctness.

## State and risk representation

`RadsStateEncoder` converts a `DispatchProblem` plus a bounded risk profile into
an immutable state. Each candidate has a stable distance feature and a
`RiskSignal` containing finite failure probability and impact minutes. The
encoder emits a canonical state digest and rejects missing, duplicate, or
non-finite risk values. A risk profile is an experiment input, not durable
business truth; production risk ownership remains outside this module.

## Objective and selector

`RadsObjective` computes:

`distance_weight * distance_km + risk_weight * failure_probability * impact_minutes`

Weights must be finite and non-negative, with at least one positive weight.
`RadsSelector` ranks candidates by `(objective, courier_id)` and returns an
immutable `RadsSelection` containing the chosen courier, score breakdown,
state digest, and bounded human-readable explanation. Empty candidate sets
produce an explicit unassigned selection.

## Comparison and experiments

`RadsExperimentManifest` records code/scenario identity, seed, registered
baseline names, objective weights, ablation variants, risk multipliers, and
configuration metadata. Canonical serialization gives every manifest a stable
digest. `RadsExperimentRunner` evaluates RADS variants on one encoded problem
and solves the same problem through the requested registered baselines. Results
include assignment, objective terms, explanations, and deterministic output
digests; wall-clock time is not included in the digest.

The built-in variants are `full`, `distance-only`, and `risk-only`. Robustness
is represented by explicit positive risk multipliers, so changed assumptions
produce a changed manifest/output digest while repeated runs remain byte
identical. The runner does not mutate the registry or scenario state.

## Evidence boundary

Tests cover state/risk validation, deterministic tie-breaking, objective
breakdowns, explanations, baseline comparison, ablation, robustness, and
repeated-run digests. Reduced fixture experiments are local and do not claim
production uplift, live-provider accuracy, or large-scale performance.
