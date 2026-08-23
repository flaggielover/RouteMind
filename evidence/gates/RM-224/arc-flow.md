# RM-224 Data-Backed Arc and Flow Evidence

Date: 2026-08-24
Implementation checkpoint: pending commit
GitHub Actions: pending remote validation

## Scope

The Operations surface now includes a flow projection derived from
route-bearing order records in the selected `OperationsSnapshot`. Endpoint
coordinates are assigned to source and destination areas, then aggregated by
area pair. The panel renders bounded arcs, directional flow records, order
volume, mean confidence, minute-level recency, and selectable order evidence.

The projection labels `LIVE`, `DEMO`, `REPLAY`, or `SIMULATION` source mode and
renders fresh, stale, empty, route-less, and unavailable states. Decorative
arcs without an underlying route record are not produced.

## Local evidence

- `npm run check` in `apps/web` - PASS, 66 unit tests across 21 files,
  Prettier, ESLint, TypeScript, and production build.
- `./scripts/web.ps1 e2e` - PASS, 34 browser tests with 2 existing
  desktop-only skips across desktop/mobile role routes, viewport checks, and
  accessibility smoke.
- `./scripts/business-api.ps1 -Action test` - PASS, Java 80 tests (same
  unchanged runtime baseline used for this Web-only task).
- `./scripts/compute-api.ps1 -Action check` - PASS, Python 208 tests at
  95.29% coverage (same unchanged compute baseline used for this Web-only
  task).
- `python scripts/validate_control_plane.py` - PASS.
- Local `docker version` and `docker compose config --quiet` remained blocked
  by an unresponsive Docker Desktop engine pipe; remote Compose validation is
  required before closure.

## Boundary and limitations

Flow areas are a descriptive nearest-zone projection over snapshot coordinates;
they are not geocoded service areas, route instructions, or a new durable
record. Recency is snapshot age, not event-level causal latency. Confidence
communicates projection lineage and geometry quality, not dispatch correctness.

## Remote validation

To be filled after the checkpoint is pushed and all five GitHub Actions jobs
complete successfully.
