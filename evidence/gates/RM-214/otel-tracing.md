# RM-214 OpenTelemetry Tracing Evidence

Date: 2026-08-23
Implementation checkpoint: pending commit
GitHub Actions: pending implementation run

## Scope

- Spring Boot 4.1 Micrometer-to-OpenTelemetry tracing with optional OTLP export
- Python application-scoped OpenTelemetry SDK with optional OTLP/HTTP export
- W3C `traceparent` extraction/continuation and legacy `X-Trace-Id` compatibility
- Java HTTP, database, Rabbit publish, and durable decision observations
- Python HTTP, travel point/matrix, solver, and decision-verification spans
- Event, aggregate/order, correlation, request, and decision identity attributes
- Collector-free in-memory observation/span evidence

## Executable evidence

Command: `./scripts/business-api.ps1 -Action test`

Result: PASS - 71 tests. The suite verifies an incoming W3C trace ID is
continued by the HTTP server, all three explicit Java boundary observations are
recorded with business identity, and Rabbit messages preserve trace,
correlation, event, and aggregate headers. The Spring application context runs
with OTLP export disabled.

Command: `./scripts/compute-api.ps1 -Action check`

Result: PASS - Ruff lint/format, strict mypy, five schemas/15 contract fixtures,
185 tests at 95.24% coverage, deterministic replay, append-only archive,
DuckDB mart, and semantic metric gates. Four focused tracing tests use an
in-memory exporter to prove W3C and legacy parent relationships, HTTP identity,
one shared travel/solver/verification trace, and disabled-SDK behavior.

Command: `./scripts/resilience.ps1`

Result: PASS - 14 Java HTTP/resilience tests and two Python deterministic
dependency-failure tests. The focused gate retained bounded travel fallback and
durable degradation behavior with tracing enabled and OTLP export disabled.

## Boundaries

- Tracing and export are never business correctness dependencies.
- PostgreSQL and Java remain authoritative for durable state and decisions.
- OTLP export is disabled by default and collector credentials are not stored.
- No production collector, retention, sampling-performance, or vendor claim is
  made by this evidence.
