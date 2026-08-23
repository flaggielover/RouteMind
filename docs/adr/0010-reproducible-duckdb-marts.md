# ADR-0010: Reproducible In-Process DuckDB Marts

Status: Accepted  
Date: 2026-08-23  
Decision task: RM-212

## Context

RM-211 provides an append-only, manifest-verified JSONL archive under the
external data root. Enhancement analytics need SQL facts and dimensions without
querying PostgreSQL OLTP state ad hoc or introducing a network analytical
service. Rebuilds must remain evidence-linked and repeatable.

## Decision

Use pinned DuckDB `1.5.5` through a dedicated connection to
`ROUTEMIND_DATA_ROOT/marts/routemind.duckdb`. The builder verifies every source
partition SHA-256 from the RM-211 manifest before loading. It maintains a generic
`fact_event` source table, curated dataset views (`fact_decision`, `fact_order`,
`fact_order_transition`, `fact_location_observation`, `fact_solver_run`, and
`fact_simulation_run`), and the first justified dimension, `dim_strategy`.

Full mode builds a temporary database and atomically replaces the target.
Incremental mode inserts by globally unique `record_id` with conflict-ignore
semantics, then rebuilds derived dimensions. Results record source partition and
record counts, inserted count, total mart count, a stable source digest, and a
canonical content digest. Digest stability applies to logical content rather
than DuckDB file bytes.

## Consequences

- DuckDB is an in-process read model, never business authority.
- No global/shared DuckDB connection, online extension, or new deployable is
  introduced.
- JSONL remains the source archive; Parquet materialization stays optional and
  evidence-driven.
- Multi-writer production coordination, scheduling, retention, and object-store
  delivery remain explicit later concerns.
