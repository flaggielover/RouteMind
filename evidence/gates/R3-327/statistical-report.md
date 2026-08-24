# R3-327 Statistical RouteBench report

Date: 2026-08-24 (Asia/Shanghai)

## Source and lineage

This report is a read-only projection of the retained material pilot; it does
not execute a strategy, change a seed, or reinterpret R3-325. The source
campaign is
`F:\Projects\RouteMind-Data\experiments\r3\R3-325\r3-325-pilot-20260824-ce8dafb`.

- Protocol: `r3-320-statistical-routebench-v1`
- Protocol SHA-256: `a6dae9d55641ff7966ef4a50cc00a63da3e936620c3c48f23cd2c2ce039375b5`
- Implementation revision: `ce8dafb65358b9ae0250a0ddc3973bd2ca59eb1f`
- Implementation CI: Actions run `32725900984`, completed successfully
- Campaign plan digest: `8880268766523069ad3db523a5babf2170eed47a34489d2850c89a46c76929be`
- Pilot ledger digest: `d8c00899785cc9c9cfd7bd7eac1a25513d8131a1c992b60e106ba12709bc5d76`
- Pilot analysis digest: `5c1c0963b3cb9d8809dd7d02355ef6f401ddd8c69b55dc1d6dc74c17a898a10c`
- Statistical report digest: `0c7e29af8c89ed9ca7cb094525745f488c4b4d69e73ab6a4a7f47dd4e5ae9eac`

The generator verified every JSON artifact and SHA-256 sidecar, plan/ledger/
analysis content digest, protocol manifest identity, and all 64 pair identities
before producing `statistical-report.json`. The final external directory has
69 JSON artifacts and 69 matching sidecars, totaling 2,561,169 bytes, below the
frozen 512 MiB artifact envelope.

## Report contents

The report contains all 16 regime/metric identities, `n=8` for every paired
cell, every four-stream seed and stream digest, candidate/comparator/difference
value distributions (values, min/p05/p25/median/mean/p75/p95/max and sample SD),
the retained Student-t interval, paired Cohen's dz, winsorized and leave-one-out
sensitivity where estimable, prospective power planning lineage, scenario
manifest digests, generator/strategy versions, and per-cell runtime,
strategy-failure, fallback, timeout, and outcome diagnostics. It also retains a
16-test Holm family table with raw and adjusted p-values explicitly null because
no confirmatory campaign was executed.

Observed pilot coverage is 64/64 complete pairs and 128/128 completed arm
attempts. Runtime diagnostics contain 128 completed arms, zero strategy
failures, zero fallbacks, and zero timeouts. Across all arms, runtime has mean
7.620174 ms, median 7.061300 ms, p95 12.893200 ms, and maximum 16.251000 ms.

## Statistical disposition

Ten family cells have an estimable paired estimate and retained prospective
power plan. Six assignment-rate cells are explicitly
`NON_ESTIMABLE_PAIRED_VARIANCE_OR_POWER` because their paired differences have
zero variance: `normal`, `surge`, `merchant-delay`, `travel-degradation`,
`location-staleness`, and `compute-budget`. Their raw/adjusted p-values remain
null; no confirmatory inference was attempted. The report disposition is
`CONFIRMATORY_NOT_EXECUTED`.

R3-B1 therefore remains `S-FAIL / C-NO-CLAIM`. The report is an auditable
descriptive and negative-result artifact, not evidence of risk-aware superiority
or assignment non-inferiority. Formatting cannot promote a scientific claim.

## Engineering gates

- Focused report tests: 5 passed; source/test Ruff and strict mypy: PASS.
- Report CLI rerun against the material F-drive campaign: PASS and idempotent.
- `uv lock --check --project services/compute-api`: PASS (the entrypoint adds no
  dependency changes).
- The preceding full local gate and remote Actions run `32726521147` remain
  green for the R3-325 closure checkpoint.

Final task disposition: `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.
