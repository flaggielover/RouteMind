# R3-344 Safe-RADS Constraint Semantics

Date: 2026-08-25 (Asia/Shanghai)
Status: passed as a preregistration-only formalization
Implementation checkpoint: `65c992fce1b73495c01b650996c167fe9c7ec86e`
GitHub Actions: PASS - run `32759977254` (all five jobs)

## Frozen contract

Manifest: `docs/research/r3/manifests/rads/r3-344-safe-rads-formalization-v1.json`

- Canonical digest: `82fed4dc95bec7ccbfa10ead770d63e2de6f47bb081d0b5d05672382462f6644`
- Byte SHA-256: `a3570615177b19fa59688b23a0e85f76957c6090b75f1fd6d165f3506b171163`
- Primary constraint: `late_service_probability <= 0.05`.
- Uncertainty: one-sided Wilson upper bound at 95% confidence, requiring at
  least 100 observations and explicit calibration.
- Efficiency: route-cost relative bound `+0.03`, reported separately from
  safety feasibility.

The contract distinguishes four non-interchangeable semantics: hard means a
violating candidate is infeasible; chance means a probability bound under a
declared uncertainty model; risk means an expected/quantile/tail-risk quantity;
penalty means an objective weight and can never establish safety. Hard-violation
fallback is rejection or a verified safe fallback. Calibration or uncertainty
failure rejects the candidate and emits no claim. Penalty-only execution and
safety wording are explicitly forbidden.

Python owns only the proposal boundary. The Java durable assignment boundary
must verify hard constraints before commit, preserving the Java/Python split and
preventing Python or an LLM from owning durable dispatch correctness.

## Executable evidence

- Targeted Safe-RADS loader tests: 6/6 passed, including identity, digest,
  semantic, threshold, uncertainty, fallback, authority, execution-policy,
  lineage, and nested-type fail-closed branches.
- `./scripts/compute-api.ps1 -Action check`: PASS - 860/860 Python tests,
  95.72% total coverage, Ruff, strict mypy, schemas/contracts, determinism,
  analytics, semantic metrics, and repository controls.
- GitHub Actions run `32759977254`: PASS for Java, Python/contracts,
  Web/browser smoke, control-plane/Compose, and bounded degradation/resilience.

## Final disposition

R3-344 closes `E-PASS / X-NOT-REQUIRED / S-NOT-APPLICABLE / C-DEFERRED`.
The formal contract authorizes a future evidence-bearing Safe-RADS experiment;
it does not establish safety, service non-inferiority, efficiency, calibration,
or superiority.
