# Science Readiness Audit Evidence

Date: 2026-08-28 (Asia/Shanghai)
Audited revision: `ab585f82fbcdd68aaa75cf8597d7f68be6c385aa`
Scope: repository-local and CI-ready inspection only. No provider, cloud,
paid API, credential, or scientific discovery was executed.

## Decision

`SCIENCE_READY_WITH_NONBLOCKING_GAPS`

`CLAUDE_SCIENCE_CAN_START = YES` for bounded exploratory discovery, hypothesis
generation, experiment design, deterministic replay, and falsifiable local
studies. No confirmatory, external-validity, production, causal, novelty,
Twin-fidelity, RADS-superiority, or strategy-superiority claim is authorized.

## Evidence inventory

- Round 3 closure: `docs/research/r3/ROUND_3_SCIENTIFIC_CLOSURE_REPORT.md`.
- Frozen statistical protocol and report: `docs/research/r3/manifests/statistical-routebench/statistical-routebench-v1.json`, `evidence/gates/R3-325/robustness-matrix.md`, and `evidence/gates/R3-327/statistical-report.md`.
- Twin split/fidelity/non-fidelity: `evidence/gates/R3-330` through `evidence/gates/R3-336`.
- RADS formal, ablation, and robustness audits: `evidence/gates/R3-340` through `evidence/gates/R3-349`.
- Decision Corpus and independent reproduction: `evidence/gates/R3-350`, `evidence/gates/R3-356`.
- Append-only negative results and claim matrix: `docs/research/r3/NEGATIVE_RESULTS.md`, `docs/research/r3/CLAIM_MATRIX.md`.

## Gate record

| Gate | Result |
| --- | --- |
| S1 reproducible experiment execution | `PARTIAL_NONBLOCKING` |
| S2 RouteBench | `PARTIAL_NONBLOCKING` |
| S3 Digital Twin | `PARTIAL_NONBLOCKING` |
| S4 policy/RADS | `PARTIAL_NONBLOCKING` |
| S5 metrics | `PARTIAL_NONBLOCKING` |
| S6 ablation/stress | `PARTIAL_NONBLOCKING` |
| S7 research lineage | `PARTIAL_NONBLOCKING` |
| S8 Linux campaign readiness | `PARTIAL_NONBLOCKING` |

No `FAIL_BLOCKING` gate was found for the scoped exploratory start. The true
high-scale Linux blocker is the absence of a remote launcher/worker scheduler
and artifact synchronization/checkpoint transfer protocol. Missing observed
Twin/RADS outcomes block their claims, not local experiment design.

## Local checks performed

- `python scripts/path_safety_test.py`: 9 tests passed.
- `python scripts/negative_results_gate.py`: valid, 31 frozen entries.
- `python scripts/claim_matrix_gate.py`: valid, 7 claim rows and zero `C-PASS`.
- `python scripts/round4_graph_gate.py`: valid active 38-task graph.
- `ROUTEMIND_DATA_ROOT` presence-only check in the audit process: `MISSING`.
  The code fails closed when the variable is absent; no data directory was
  created or modified.
- Targeted research tests were run with the repository's uv environment and
  all selected test cases passed. Subset invocations reported the configured
  global 95% coverage threshold because they intentionally did not load the
  complete suite; this is not a product failure. The authoritative full gate
  remains `scripts/verify.ps1`.
- `./scripts/compute-api.ps1 check`: 938 tests passed, 95.10% total coverage,
  Ruff/mypy/package/contract checks passed. The deterministic CI audit emitted
  identical scenario digests `869d09da5afacf54af013c9d049d6165a100cd4b20bd773aa89f43b8e978dbce`
  for both runs.
- `./scripts/verify.ps1`: passed control-plane, negative-results, claim-matrix,
  scientific-figures, Round 4, security, supply-chain, all external-validation
  preparation contracts, product, provider-retirement, and agent-authority
  gates. No provider call or resource mutation occurred.

## Frozen boundaries

R3-325 remains exactly `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`. R4-405/R4-406,
VKE/VM/SSH, R4-411B, R4-422, and retired HERE states are unchanged. This audit
adds no scientific result and performs no external call.

## Handoff files

- `research/SCIENCE_CONTEXT.md`
- `research/SCIENCE_READINESS.md`
- `research/RESEARCH_CANDIDATES.md`
- `research/EXPERIMENT_INTERFACE.md`
- `research/KNOWN_NEGATIVE_RESULTS.md`
- `research/CLAIM_BOUNDARIES.md`
