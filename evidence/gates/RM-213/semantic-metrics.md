# RM-213 Semantic Metrics Evidence

Date: 2026-08-23  
Implementation checkpoint: pending commit after local validation

## Scope

- Central executable registry with seven named metrics
- Exact unit, source fields, aggregation, numerator, denominator, event-time,
  consumer, and unavailable-data declarations
- SHA-256 definition lineage included in catalog contracts and query results
- Read-only DuckDB engine with registry-selected source views and expressions
- One catalog contract for Web, report, and agent consumers
- `GET /api/v1/analytics/metrics/catalog` without executable SQL exposure
- Typed Web data adapter that requests the registry-owned `consumer=web` view

## Executable evidence

Command: `./scripts/compute-api.ps1 -Action check`

Expected coverage:

- Ruff lint and format
- strict mypy
- schema and fixture contracts
- full Compute test suite and coverage threshold
- determinism, archive, mart, and semantic metric gates
- zero-denominator unavailable behavior
- UTC half-open window behavior
- recognized-status denominator filtering
- missing mart, invalid window, and unknown metric rejection
- API catalog filtering and arbitrary-consumer rejection

Command: `python ../../scripts/semantic_metrics_gate.py` through frozen uv

Expected deterministic result:

```json
{"consumer_catalog_consistent":true,"metric_count":7,"results":{"dispatch_assignment_rate":0.5,"dispatch_fallback_rate":0.5}}
```

Command: `./scripts/web.ps1 -Action check`

Expected coverage includes the typed Web adapter request, lineage mapping, and
explicit HTTP failure behavior without duplicating a metric calculation.

Local result: PASS - 181 Compute tests at 95.25% coverage and 51 Web tests;
all listed static, contract, deterministic, analytical, and build gates passed.

## Boundaries

- The engine connects to the mart read-only.
- Definitions are static application code, not caller-supplied SQL.
- Metrics are analytical read models and cannot mutate Java-owned business state.
- No dataset, DuckDB database, or other large analytical artifact is committed.
