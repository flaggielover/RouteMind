# RM-050 Evidence: Seeded Digital Twin Scenario Kernel

Date: 2026-08-22

## Gates

- `scripts/full-gate.ps1`: PASS.
- 32 Python tests passed with 97.92% statement and branch coverage.
- Ruff, strict mypy, and all 4 schemas / 12 contract fixtures passed.

## Behavior

- `ScenarioManifest` captures scenario identity, seed, demand events, courier
  supply, delay choices, and traffic multiplier with validation.
- `ScenarioKernel` orders events by `(tick, request_id)`, delegates to the
  dispatch registry and travel provider, and emits `ASSIGNED` or `UNASSIGNED`
  state transitions while updating courier availability.
- Canonical JSON of decisions and transitions is hashed with SHA-256. Replaying
  the same manifest and seed returns an identical `ScenarioRun`; changing the
  seed changes provenance and digest.
