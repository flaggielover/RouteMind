# RM-223 City and Zone Operational Drilldown Evidence

Date: 2026-08-24
Implementation checkpoint: pending commit
GitHub Actions: pending remote validation

## Scope

The Operations surface now includes a city/zone drilldown projected from the
selected `OperationsSnapshot`. It exposes orders, merchants, courier supply,
service-area zone labels, density per 100 orders, bounded risk, and
descriptive route counts. A bounded zoom control switches city aggregation to
zone detail. Source labels and freshness states are visible for live, demo,
replay, simulation, stale, empty, and unavailable snapshots.

## Local evidence

- `npm run check` in `apps/web` - PASS, 62 unit tests, Prettier, ESLint,
  TypeScript, and production build.
- `./scripts/web.ps1 e2e` - PASS, 34 browser tests with 2 existing
  desktop-only skips across desktop/mobile role routes and accessibility
  smoke.
- `./scripts/business-api.ps1 -Action test` - PASS, Java 80 tests.
- `./scripts/compute-api.ps1 -Action check` - PASS, Python 208 tests at
  95.29% coverage, schemas, formatting, lint, and determinism evidence.
- `./scripts/verify.ps1` reached all repository checks before the local
  Docker Compose probe; `docker compose config --quiet` could not complete
  because the local Docker Desktop engine pipe was unresponsive. The remote
  control-plane/Compose job remains the authoritative Compose validation.

## Boundary and limitations

Zone membership is derived from existing courier zone labels and schematic
route coordinates for this read-only projection. It is descriptive, not a
new durable record, and does not replace Java lifecycle state. Empty and
unavailable sources render honest states rather than inferred zero supply.

## Remote validation

To be filled after the checkpoint is pushed and all five GitHub Actions jobs
complete successfully.
