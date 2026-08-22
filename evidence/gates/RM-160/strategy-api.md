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
- Java, repository integrity, contracts, Python, and Web format/lint/type checks: passed during the full-gate attempt.

## Remaining gate
Web Vitest could not start because the current Windows sandbox returns `spawn EPERM`. RM-160 remains `in_progress`; no remote Actions pass is claimed.
