# RM-031 Evidence: Weighted Greedy and Hungarian Baselines

Date: 2026-08-22

## Gates

- `scripts/full-gate.ps1`: PASS.
- 26 Python tests passed; total statement/branch coverage is 96.43%.
- Ruff, strict mypy, and all 4 schemas / 12 contract fixtures passed.

## Behavior

- `WeightedGreedyStrategy` and `HungarianStrategy` conform to the RM-030
  versioned registry contract and produce deterministic decisions.
- Hungarian assignment handles square, rectangular, and transposed matrices,
  rejects ragged/non-finite input, and returns stable row/column pairs.
- `benchmark_problem` runs registered strategies and records strategy name,
  version, latency, selected courier, and caller-supplied provenance
  (`rm031-smoke-v1` in the test gate).
