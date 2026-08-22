# RM-161 Strategy Parameters and Experiments

## Implemented contract

- `StrategyParameterSchema` publishes versioned, typed, bounded numeric
  parameters with defaults and validation. Weighted-greedy exposes
  `distance_weight`; risk-aware exposes its five non-negative scoring weights;
  other registered strategies publish an empty schema.
- `StrategyRegistry.solve` accepts an optional parameter configuration and
  creates a bounded, ephemeral configured strategy. No strategy configuration
  becomes durable business state.
- `POST /api/v1/experiments/routebench` reuses the existing seeded
  `RouteBenchRunner` and `ScenarioKernel`, recording manifest/output digests,
  scenario, seed, generic manifest configuration, parameter configuration,
  per-strategy runtime observations, assignment metrics, and replay digests.

## Local evidence

- Compute check: 109 tests passed at 95.39% total statement/branch coverage;
  Ruff, format, mypy, and contract validation passed.
- Full available gate: Java 60 tests, Python 109 tests, Web 38 unit tests/build,
  and 5 schemas/15 fixtures passed.
- Parameter and experiment tests cover schema defaults, bounds, duplicate and
  unknown keys, sorted catalog metadata, configured baselines, deterministic
  manifest/output provenance, and bounded API inputs.

## Gate decision

Local L2 strategy-parameter and L6 experiment-provenance evidence is complete.
GitHub Actions run `32600780985` passed all five required jobs, so RM-161 is
fully validated.
