# Known Negative Results

The following outcomes are intentionally preserved and must not be optimized
away:

- R3-325: `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`; confirmatory inference was
  not executed and no strategy-superiority claim exists.
- Twin calibration/held-out/fidelity work: zero eligible observed records;
  status remains `INSUFFICIENT_DATA` and no synthetic substitute is allowed.
- RADS-H, Safe-RADS, ablation, policy-boundary, counterfactual, and robustness
  audits: required outcome logs/support are absent, so broad empirical claims
  remain prohibited.
- OPE: `OPE_NOT_IDENTIFIABLE_FROM_CURRENT_LOGS`; no propensity or causal
  estimator was fabricated.
- R4-411B Google validation: ComputeRoutes passed and ComputeRouteMatrix was
  partial; `FAILED / PARTIAL_NO_PRODUCTION_CLAIM` remains frozen.
- VKE, Tokyo VM, and SSH readiness validations: inconclusive/diagnostic
  incomplete records remain retained with zero retained resources after
  teardown; no target or root-cause claim exists.

The authoritative append-only Round 3 negative-result ledger is
`docs/research/r3/NEGATIVE_RESULTS.md`, guarded by
`scripts/negative_results_gate.py`.
