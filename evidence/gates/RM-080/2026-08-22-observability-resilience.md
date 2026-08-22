# RM-080 Observability and Resilience Gate

- Time: 2026-08-22T12:41:11+08:00
- Revision before checkpoint: `9eaada1675f02e182d55753005982bbaba5296cd`
- Worktree: RM-080 changes present; no unrelated files
- Boundary: local deterministic and CI evidence; no production collector or load claim

## Commands and results

1. `./scripts/compute-api.ps1 check` - PASS
   - Ruff, format, strict mypy, 4 schemas / 12 fixtures, 36 Python tests.
   - Total statement/branch coverage: 98.07% (required 95%).
   - The API observability tests include a fixed 100-request bounded burst; all responses returned HTTP 200 and the bounded metric series was present.
2. `./scripts/business-api.ps1 resilience` - PASS
   - Java 17 compilation and 4 `BusinessApiApplicationTests` passed.
   - Request and trace headers were propagated and the Micrometer Prometheus `/metrics` endpoint exposed request counters.
3. `./scripts/compute-api.ps1 resilience` - PASS
   - Injected travel-provider timeout and matrix failure both selected the deterministic local fallback with explicit fallback metadata.
4. `./scripts/full-gate.ps1` - PASS
   - Control plane, Compose, PowerShell syntax, Java 34 tests, Python 36 tests, 98.07% coverage, contracts, Web static/unit/build gates passed.

## Implemented boundary

Java and Python independently accept or generate bounded `X-Request-Id` and
`X-Trace-Id`, return the identifiers, log structured request completion, and
publish bounded request count/latency metrics. Java uses an explicit Micrometer
Prometheus registry-backed `/metrics` endpoint; Python uses `prometheus-client`.
Runbooks document health checks, SLI names/labels, degraded behavior, and
intervention/rollback paths. Redis projection loss and travel-provider failure
remain bounded without moving durable truth to a hot-state dependency.

## Evidence limits

This gate does not claim production tracing, external collector delivery,
concurrent load capacity, alert thresholds, or vendor-specific dashboards.
