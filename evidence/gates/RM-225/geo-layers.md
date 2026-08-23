# RM-225 Toggleable Geo Analytical Layers Evidence

Date: 2026-08-24
Implementation checkpoint: pending commit
GitHub Actions: pending remote validation

## Scope

The Operations surface now includes toggleable analytical layers over the
selected snapshot and RM-224 flow records. Enabled layers expose order demand,
available courier supply, supply gap, SLA risk, courier utilization, and order
flow. Each value carries a local unit, scale, and source-record count.

Congestion and travel degradation are visible as disabled because the current
snapshot has no provider travel metric. Location integrity is enabled only when
courier sequence/freshness/online metadata is present. No missing metric is
represented as zero.

## Local evidence

- `npm run check` in `apps/web` - PASS, 70 unit tests across 23 files,
  Prettier, ESLint, TypeScript, and production build.
- `./scripts/web.ps1 e2e` - PASS, 34 browser tests with 2 existing
  desktop-only skips across desktop/mobile role routes, viewport checks, and
  accessibility smoke.
- `./scripts/business-api.ps1 -Action test` - PASS, Java 80 tests (unchanged
  runtime baseline).
- `./scripts/compute-api.ps1 -Action check` - PASS, Python 208 tests at
  95.29% coverage (unchanged compute baseline).
- `python scripts/validate_control_plane.py` - PASS.
- Local Docker engine remains unresponsive for `docker compose config --quiet`;
  remote control-plane/Compose validation is required for closure.

## Boundary and limitations

Layer values are bounded analytical projections, not raw map points, travel
instructions, or durable records. Deferred layers are intentionally
unavailable until their source contracts carry the required metrics.

## Remote validation

To be filled after the checkpoint is pushed and all five GitHub Actions jobs
complete successfully.
