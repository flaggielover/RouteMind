# R3-349 RADS Cross-Regime Robustness Support Audit

Date: 2026-08-25 (Asia/Shanghai)
Status: closed as a read-only `INSUFFICIENT_DATA` support audit
Implementation checkpoint: `94f1a3e3000fa645a775f3ffca3de3157bf3df97`
GitHub Actions: PASS - run `32777694427` (all five jobs)

## Frozen robustness boundary

Manifest: `docs/research/r3/manifests/rads/r3-349-rads-robustness-v1.json`

- Canonical digest:
  `379f5087f3114f50cd9bb8cefff62af0d9a35e0ea3e1ba12544b9fafc52527a2`
- Byte SHA-256:
  `e58abf5ac7498a3564c3a9dc7d001ae34da2d79ccde6a54d41a2c4fc091d7f5b`
- Frozen axes: seeds, demand, supply, merchant delay, traffic, location noise,
  location staleness, and compute constraints.
- Frozen metrics: assignment rate, route cost, service metric, switching rate,
  constraint violation, fallback rate, and dispatch latency.
- Each axis level requires at least 30 paired seed/regime/stream units.
  Continuous uncertainty uses paired-bootstrap percentile 95% intervals with
  2,000 resamples; multiplicity uses Holm over the axis-metric family.
- Broad wording is eligible only if every axis is supported and every
  preregistered cross-regime test passes. One favorable scenario is never
  sufficient.

## Read-only support audit

R3-325 remains exactly frozen at
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`; it was not rerun, tuned,
reinterpreted, or optimized. Its immutable pilot artifacts preserve seed/CRN
identity and source regimes for demand, supply, merchant delay, traffic,
location staleness, and compute pressure. They do not preserve a location-noise
regime or RADS-H/Safe-RADS strategy identity and outcomes.

The audit therefore returned `INSUFFICIENT_DATA`:

- seeds, demand, supply, merchant delay, traffic, location staleness, and
  compute constraints are `SOURCE_REGIME_PRESENT_NO_RADS_OUTCOME`;
- location noise is `UNSUPPORTED_REGIME_NOT_PRESENT`;
- the retained eight pairs per existing regime are below the frozen minimum
  of 30;
- all seven metrics are `NOT_REPORTED_NO_CROSS_REGIME_RADS_OUTCOMES`; and
- broad claim status is `PROHIBITED_NO_CROSS_REGIME_EVIDENCE`.

No material campaign, synthetic fill, favorable-scenario selection, external
write, robustness effect, uncertainty interval, superiority result, or broad
RADS robustness claim was produced.

## Executable evidence

- Targeted R3-349 tests: 6/6 passed, covering current source support,
  unsupported location noise, absent RADS outcomes, pair-count threshold,
  complete support, and fail-closed input/manifest drift.
- `./scripts/full-gate.ps1`: PASS - Java 81/81, Python 893/893 at 95.08%
  total coverage, Web 92/92 plus production build/browser smoke, Ruff,
  formatting, strict mypy, six schemas/18 fixtures, determinism, analytics,
  semantic metrics, repository controls, and bounded resilience.
- GitHub Actions run `32777694427`: all five jobs passed for implementation
  SHA `94f1a3e3000fa645a775f3ffca3de3157bf3df97`.

## Final disposition

R3-349 closes `E-PASS / X-PASS / S-NOT-APPLICABLE / C-NO-CLAIM`.
The support audit is reproducible and explicitly preserves unsupported axes;
current evidence does not establish cross-regime RADS robustness.
