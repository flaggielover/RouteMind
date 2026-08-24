# R3-343 Empirical Switching Stability-Map Support Audit

Date: 2026-08-25 (Asia/Shanghai)
Status: closed as a read-only `INSUFFICIENT_DATA` support audit
Implementation checkpoint: `44df8e2c1215230ca5a7ee24f13f87d708050bcc`
GitHub Actions: PASS - run `32776065978` (all five jobs)

## Frozen empirical map boundary

Manifest: `docs/research/r3/manifests/rads/r3-343-stability-map-v1.json`

- Canonical digest:
  `c6d7d4a5ac088570731e80a189c12cd79792256ac3669bdeed5f9049d6b4ee14`
- Byte SHA-256:
  `8153eeef5f5397ae411371eedb9c369995ba1cdc33057814a9923613213e49c6`
- Frozen axes: relative advantage, dwell ticks, pressure ticks, regime
  identity, and active-to-candidate strategy pair.
- Frozen outputs: selection rate, switching rate, service metric, route cost,
  and instability rate.
- A cell requires at least 30 observations. Unobserved and underpowered cells
  remain explicitly unsupported. Proportions use Wilson 95% intervals and
  continuous metrics use paired-bootstrap percentile intervals over paired
  seed/regime/stream units.
- The interpretation is always `EMPIRICAL_ONLY_NOT_THEORETICAL`.

## Read-only support audit

R3-325 remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`. Its immutable aggregate pair
summaries do not contain any of the eight required fields:

- `tick_state_observations`
- `strategy_selections`
- `switch_events`
- `service_outcomes`
- `route_cost_outcomes`
- `instability_observations`
- `regime_identity`
- `pairing_unit`

The audit returned `INSUFFICIENT_DATA`,
`NO_ELIGIBLE_CELLS`, and `NOT_ESTIMATED_NO_CELL_SUPPORT`. All five axes
are `NOT_MAPPED_NO_TICK_LOGS`; all five outputs are
`NOT_REPORTED_NO_TICK_LOGS`. No material campaign, synthetic map, R3-325
rerun, external write, stability region, uncertainty interval, performance
effect, or theoretical-stability claim was produced.

## Executable evidence

- Targeted R3-343 tests: 6/6 passed, covering missing/complete support and
  rejection of digest, identity, axis, coverage, uncertainty, support,
  lineage, execution-policy, and theoretical-claim drift.
- `./scripts/compute-api.ps1 -Action check`: PASS - 887/887 Python tests at
  95.26% total coverage, Ruff, formatting, strict mypy, six schemas/18
  fixtures, determinism, analytics, and semantic metrics.
- GitHub Actions run `32776065978`: all five jobs passed for implementation
  SHA `44df8e2c1215230ca5a7ee24f13f87d708050bcc`.

## Final disposition

R3-343 closes `E-PASS / X-PASS / S-NOT-APPLICABLE / C-NO-CLAIM`.
The map contract is reproducible, but there is no empirical map or stability
claim from the current logs.
