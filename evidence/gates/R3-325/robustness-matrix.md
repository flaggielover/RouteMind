# R3-325 preregistered RouteBench robustness matrix

Date: 2026-08-24 (Asia/Shanghai)

Base revision for this implementation checkpoint: `a6e85f5e0a5cb035a4c44b9d2ef5387ac9cbeac7`

## Scope and execution boundary

R3-325 implements a manifest-bound pilot and confirmatory campaign runner for
the frozen R3-320 Statistical RouteBench protocol. The runner binds the full
implementation SHA and a completed successful GitHub Actions run before a
material campaign can start. Campaigns are restricted to `main`, a clean
tracked worktree, `origin/main`, and the declared external data root.

The frozen matrix contains eight numeric regimes (normal, surge, shortage,
merchant delay, travel degradation, location staleness, compute budget, and
queue pressure), eight pilot pairs per regime, four common-random-number
streams, parity-alternated arm order, and disjoint confirmatory replicate
identities. The candidate and comparator remain the preregistered
`risk-aware@1.0.0` and `weighted-greedy@1.0.0` strategies. No regime or seed
was selected after inspecting results.

## Resource estimate

The pilot plan is 8 regimes x 8 pairs = 64 pairs and 128 arm runs. Each arm is
single-threaded with a 30-second wall timeout, giving a 3,840-second maximum
arm budget, 1,024 MiB expected peak memory, 512 MiB maximum external artifact
envelope, and USD 0 external cost. Confirmatory execution uses the frozen
power-plan count and cannot exceed the protocol's 3,840-arm envelope. The
estimate is serialized in the campaign plan before execution and is checked by
the artifact store on every write and resume.

## Synthetic validation (not material evidence)

An actual local execution of the complete pilot-shaped matrix exercised all 64
pairs and 128 arm attempts in approximately 1.356 seconds. The run retained
scenario, stream, event, timing, outcome, and failure fields and did not write
to the material external data root. In this environment, assignment-rate
paired variance was zero for seven regimes in the first synthetic run; a
diagnostic repeat produced assignment rate 1.0 for all eight regimes. The
analysis therefore emitted `NON_ESTIMABLE` outcomes and
`CONFIRMATORY_BLOCKED_NON_ESTIMABLE_PILOT_RETAINED`. This is an honest
environmental diagnostic, not a strategy result: no p-value, effect, power
claim, or confirmatory campaign was produced. Risk-index outcomes remained
available for audit. The frozen scenario generator was not changed to force
variance.

## Retention, lineage, and recovery

Each campaign writes immutable, write-once JSON artifacts below
`ROUTEMIND_DATA_ROOT/experiments/r3/R3-325/<campaign-id>` with SHA-256
sidecars. Plan, execution environment, every pair record, the complete ledger,
and pilot analysis retain protocol and manifest identity, implementation SHA,
CI run, runtime identity, CRN stream realization digests, arm order, event IDs,
decision timing, strategy/fallback/timeout diagnostics, and deterministic
result digests. Existing verified pair records are reused on resume; a changed
record, plan, ledger, or analysis fails closed. Harness and infrastructure
defects are retried once and remain explicitly retained; timeout and strategy
failure are scored with the preregistered worst-case value rather than dropped.

The command-line runner refuses material execution until the implementation
checkpoint is remotely green. A pilot that cannot estimate every member of the
frozen 16-test family remains retained as `S-FAIL`/`C-NO-CLAIM`; it cannot be
converted into a confirmatory design by imputation or by changing the matrix.

## Executed engineering gates

- Ruff over all compute source and tests: PASS.
- Strict mypy over all compute source and tests: PASS.
- `uv lock --check --project services/compute-api`: PASS.
- Focused R3-325 tests: PASS; analysis 100%, artifacts 96%, campaign 98%,
  local executor 100%, and runner 100% module coverage.
- `./scripts/compute-api.ps1 -Action check`: PASS, 755/755 Python tests,
  96.17% total coverage, three existing deprecation warnings.
- `./scripts/full-gate.ps1`: PASS, Java 81/81, Python 755/755 at 96.17%,
  Web 34 files / 92 tests plus production build, contracts, lock/security,
  determinism, analytics, semantic metrics, and repository controls.

## Checkpoint disposition

This file records an implementation checkpoint only. Current disposition is
`E-PASS / X-PENDING / S-PENDING / C-DEFERRED`: material pilot execution is
authorized only after this implementation is committed, pushed, and its real
GitHub Actions run is completed successfully. Synthetic output is retained as
engineering evidence and is not an observed RouteBench claim.
