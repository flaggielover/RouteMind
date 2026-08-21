# RM-040 Evidence: Travel-Model Provider Abstraction

Date: 2026-08-22

## Gates

- `scripts/full-gate.ps1`: PASS.
- 29 Python tests passed with 97.24% statement and branch coverage.
- Ruff, strict mypy, and all 4 schemas / 12 contract fixtures passed.

## Behavior

- Point and rectangular matrix travel-time contracts carry provider identity
  and validate finite non-negative seconds.
- `DeterministicLocalTravelProvider` uses Haversine distance and a configured
  constant speed, yielding reproducible point and matrix estimates.
- `FallbackTravelTimeProvider` bounds primary calls with a timeout, catches
  errors and malformed results, and marks fallback point/matrix values with
  `fallback_used=true`.
