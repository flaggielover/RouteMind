# RM-091 RADS Research Baseline Evidence

Date: 2026-08-22
Local revision before checkpoint: `e11a0ac`

## Scope

The Python compute research boundary now provides deterministic RADS state
encoding, finite risk signals, a decomposed distance/risk objective, stable
selection and tie-breaking, bounded explanations, registered-baseline
comparison, ablation variants, and explicit risk-multiplier robustness trials.
The implementation is research-only and does not own durable business state or
hard real-time dispatch correctness.

## Executed gates

`./scripts/compute-api.ps1 check` — PASS

- Ruff lint and format checks — PASS
- strict mypy — PASS
- 4 API schemas and 12 contract fixtures — PASS
- 50 Python tests — PASS
- total statement/branch coverage: 95.47% — PASS

`./scripts/full-gate.ps1` — PASS

- control-plane, Compose, and PowerShell gates — PASS
- Java: 34 tests — PASS
- Python: 50 tests, 95.47% coverage — PASS
- Web static checks, unit tests, and production build — PASS

## Reduced experiment

Fixture: one request with a near/high-risk courier and a farther/low-risk
courier. Registered baselines: `nearest`, `weighted-greedy`. RADS variants:
`full`, `distance-only`, `risk-only`. Risk multipliers: `1.0`, `2.0`.

- manifest digest: `4a5fb080443a63aa89c2a900cf0ecb60a731a2f3aa4ec2f352aa8610cd1f20e1`
- output digest: `f18a154ba5e11f319ab5c1b2adcc2283c95b7883be815ab1873b9b5632c3bc0a`
- both registered baselines selected `courier-near-risky`
- RADS `distance-only` selected `courier-near-risky`
- RADS `full` and `risk-only` selected `courier-far-safe` under both risk multipliers
- risk multiplier changes produced distinct state digests and objective components
- repeated identical runs produced the same output digest

## Behavioral evidence

- State digests are independent of risk-signal input order.
- Missing, extra, duplicate, non-finite, and out-of-range risk inputs are rejected.
- Objective results expose distance, expected risk, weighted components, and total.
- Ties are deterministic by courier identifier.
- Experiment manifests canonicalize baseline, variant, multiplier, and metadata order.
- Changed robustness assumptions change manifest and output digests.

## Limits

The evidence is a reduced local fixture. It does not claim production uplift,
live-provider risk calibration, large-scale performance, fairness, or real-world
causal validity. Those claims require separately recorded datasets, manifests,
hardware, experiments, and lineage.
