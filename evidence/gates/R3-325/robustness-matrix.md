# R3-325 preregistered RouteBench robustness matrix

Date: 2026-08-24 (Asia/Shanghai)

Implementation authorization revision: `ce8dafb65358b9ae0250a0ddc3973bd2ca59eb1f`

Implementation authorization CI run: `32725900984` (completed, success)

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

## Material pilot execution

After the authorized implementation revision was remotely green, the frozen
pilot ran once at
`F:\Projects\RouteMind-Data\experiments\r3\R3-325\r3-325-pilot-20260824-ce8dafb`.
The command returned exit code 2 exactly because confirmatory execution is
blocked when any frozen metric is non-estimable; the pilot itself completed.

- Protocol SHA-256: `a6dae9d55641ff7966ef4a50cc00a63da3e936620c3c48f23cd2c2ce039375b5`.
- Plan digest: `8880268766523069ad3db523a5babf2170eed47a34489d2850c89a46c76929be`.
- 8 regimes x 8 pairs = 64/64 complete pairs; 128 retained arm attempts.
- Pilot ledger digest: `d8c00899785cc9c9cfd7bd7eac1a25513d8131a1c992b60e106ba12709bc5d76`.
- Pilot analysis digest: `5c1c0963b3cb9d8809dd7d02355ef6f401ddd8c69b55dc1d6dc74c17a898a10c`.
- Analysis disposition: `CONFIRMATORY_BLOCKED_NON_ESTIMABLE_PILOT_RETAINED`.
  Ten of the 16 family cells were planned; six assignment-rate cells (normal,
  surge, merchant-delay, travel-degradation, location-staleness, and
  compute-budget) retained `NON_ESTIMABLE_PAIRED_VARIANCE_OR_POWER` because
  paired differences had zero variance. No imputation, scenario removal, or
  confirmatory run occurred.
- 68 non-sidecar files were written, totaling 1,974,699 bytes; all 68 SHA-256
  sidecars matched. The runner's reported artifact envelope was 1,979,119
  bytes including sidecars and remained below the 512 MiB limit.

The pilot is observed execution evidence, but it is not a positive strategy
claim. The correct statistical disposition is `S-FAIL` for the six unsupported
cells and `C-NO-CLAIM` for the campaign as a whole. Risk outcomes and all
retained pair/stream/failure lineage remain available for a later report.

## Checkpoint disposition

R3-325 disposition is `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`. Engineering
execution and artifact retention passed; the preregistered statistical gate
correctly retained six non-estimable assignment cells and refused to promote a
confirmatory design. Synthetic output remains engineering evidence and is not
mixed with the observed pilot ledger.
