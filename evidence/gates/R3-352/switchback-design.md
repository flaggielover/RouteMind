# R3-352 Simulation Switchback Design

Date: 2026-08-24 (Asia/Shanghai)
Status: passed
Implementation checkpoint: `c36881e3a9a393a09b3c136078fa753a9208db90`
GitHub Actions: PASS - run `32740971993` (all five jobs)

## Frozen design

The machine-readable preregistration is
`docs/research/r3/manifests/switchback/r3-352-switchback-v1.json`.
Its canonical design digest is
`4d3b69cf8f5bb3bea317885f4d849367aa9c8b530b35de4485820fefbe063785` and its
byte SHA-256 is
`2362a3b904b85be729f6bc29d12b63d026f4873c8df6b6a2a6d7a6d8883770a9`.
The loader reports six periods over three zones, with candidate/comparator arms
alternating at every adjacent boundary and equal block counts.

Assignment is at the `zone_time_block` level using a deterministic seeded block
sequence. Per-order randomization is explicitly prohibited. Each 30-tick block
has five warmup and five washout ticks; washout ticks are retained for carryover
diagnostics but excluded from primary summaries. The same demand and courier
streams remain common within paired blocks.

## Interference review boundary

The design preregisters shared-supply, cross-zone spillover, and state carryover
mechanisms. Each risk has an explicit unit, mitigation, and diagnostic: supply
and queue digests, cross-zone transition counts, and unfinished-order/courier
state digests at every arm boundary. Primary summaries are descriptive by
zone-time block; no claim may be made without the later R3-353 interference
analysis.

## Executable evidence

- `tests/test_switchback_design.py`: 7 directed tests cover canonical digest,
  file identity, alternating blocks, zone membership, washout, assignment unit,
  interference completeness, non-causal metrics, and fail-closed mutations.
- `./scripts/compute-api.ps1 -Action check`: PASS - 774/774 Python tests,
  95.16% total coverage, Ruff, strict mypy, 6 schemas/18 fixtures,
  determinism, analytical archive/mart, and semantic metrics.
- GitHub Actions run `32740971993`: PASS for Java, Python/contracts,
  Web/browser smoke, control-plane/Compose, and bounded degradation/resilience.

## Claim boundary

R3-352 freezes a simulation design only. It executes no simulation campaign and
does not estimate an effect, establish interference absence, support an A/B
claim, or validate a real-world causal design. Final disposition is
`E-PASS / X-NOT-REQUIRED / S-NOT-APPLICABLE / C-DEFERRED`.
