# RM-160 Strategy Registry and Execution API

## Implemented
- Compute-owned strategy catalog at `GET /api/v1/strategies`.
- Bounded execution boundary at `POST /api/v1/strategies/execute`.
- Deterministic SHA-256 provenance for canonical input and decision output.
- Explicit metrics, trace context, strategy version, and unavailable failure metadata.
- Existing live dispatch snapshot remains compatible.

## Local evidence
- Focused API, registry, and boundary tests: 12 passed.
- Full compute suite: 104 passed, 95.78% coverage.
- Ruff check: passed.
- Full available gate: Java 60 tests, Python 104 tests at 95.78%, Web 38 unit
  tests/build, and 5 schemas/15 fixtures passed.
- Browser smoke: 17 passed and 1 desktop-only test skipped; accessibility
  smoke passed for desktop and mobile routes.

## Remaining gate
Local L2/L3 strategy API evidence is complete. RM-160 remains `in_progress`
until the pushed checkpoint receives a green remote Actions run.
