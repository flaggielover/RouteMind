# R3-340 RADS-BASELINE-v1 Freeze

Date: 2026-08-25 (Asia/Shanghai)
Status: passed as a content-addressed research baseline freeze
Implementation checkpoint: `dd671f63c36bcad43f7141358da174ff51fc5400`
GitHub Actions: PASS - run `32754734242` (all five jobs)

## Frozen manifest

The machine-readable freeze is
`docs/research/r3/manifests/rads/rads-baseline-v1.json`.
Its canonical baseline digest is
`a907a0a722e8782aa76277637fa92205cc10046e5aca85b2de81e555623016c3` and its
byte SHA-256 is
`c477a1ae2b00fcd53251be26db4229c56b7e2e91d79b49f9303aba29b6014a02`.

The manifest content-addresses the existing Python RADS contracts and their
source artifacts: `RadsStateEncoder`, `RadsObjective`, `RadsSelector`, the
registered `nearest@1.0.0` and `weighted-greedy@1.0.0` controls, and the
`risk-aware@1.0.0` scoring vector. Any later baseline change requires a new
version and a new digest; this freeze is read-only and does not alter dispatch
ownership.

## Frozen semantics

- State fields are `request_id`, `risk_multiplier`, and sorted candidate records
  (`courier_id`, `distance_km`, `failure_probability`, `impact_minutes`), with a
  SHA-256 canonical state digest.
- The `full` objective uses distance weight `1.0`, risk weight `1.0`, and risk
  multiplier `1.0`: `distance_weight*distance_km + risk_weight*failure_probability*impact_minutes*risk_multiplier`.
- Risk probability is inclusive `[0, 1]`; impact is finite and non-negative;
  risk signals must exactly match candidate couriers.
- Selection ranks by `(objective_total, courier_id)` and ties use lexicographic
  courier identity. Empty candidates produce an explicit unassigned selection.
- Invalid inputs are rejected, registry failures raise, and no silent fallback
  or strategy substitution is allowed. Canonical JSON uses sorted keys,
  compact separators, UTF-8, and SHA-256; wall-clock observations are excluded
  from digests.

## Reproducible bounded execution

The existing `RadsExperimentRunner` was run against one two-courier fixture with
the frozen `nearest` and `weighted-greedy` controls and the `full` RADS variant:

- experiment manifest digest:
  `310bb5cbc6b041bbb6ee43aaafc6b0df982976913febfc39cc304483e895e155`;
- output digest:
  `3c70ebcabdd1870aaa2119585b7a9436a3a33075d9a35a5a2175b446279d646d`;
- both controls selected `near-risky`;
- RADS `full` selected `far-safe`, score `0.7048136304029549`, state digest
  `fc821868e347079e18e0e280ac20da8aa2f05a79fc9721a5271d599a5ddf13b0`.

Repeated execution is deterministic. This fixture demonstrates contract
reproducibility only; it is not a production uplift, risk calibration, safety,
fairness, scale, or causal-validity claim.

## Executable evidence

- Six directed tests pass; the R3-340 loader reaches 100% statement and branch
  coverage.
- `./scripts/compute-api.ps1 -Action check`: PASS - 837/837 Python tests,
  95.77% total coverage, Ruff and strict mypy, 6 schemas/18 fixtures,
  determinism, analytics, semantic metrics, and repository controls.
- GitHub Actions run `32754734242`: PASS for Java, Python/contracts,
  Web/browser smoke, control-plane/Compose, and bounded degradation/resilience.

## Final disposition

R3-340 closes `E-PASS / X-NOT-REQUIRED / S-NOT-APPLICABLE / C-NOT-APPLICABLE`.
The freeze establishes a reproducible baseline boundary before RADS-H and
Safe-RADS variants; it does not establish performance, safety, stability, or
scientific superiority.
