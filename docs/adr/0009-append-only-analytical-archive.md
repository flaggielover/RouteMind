# ADR-0009: External Append-Only Analytical Archive

Status: Accepted  
Date: 2026-08-23  
Decision task: RM-211

## Context

RouteMind needs analytical history for marts, semantic metrics, Decision X-Ray,
reliability, and research surfaces without making analytics an alternative
business authority. The repository has no Parquet/Arrow runtime dependency and
the configured data boundary is external (`ROUTEMIND_DATA_ROOT`).

## Decision

RM-211 adds a Python-owned `AnalyticalArchive` that appends canonical JSONL
records under `ROUTEMIND_DATA_ROOT/<dataset>/date=YYYY-MM-DD/events.jsonl`.
Every record carries schema version, event and ingestion time, clock domain,
source revision, trace/correlation identifiers, optional reference-data and
decision identities, and a JSON payload. Record IDs are globally rejected when
duplicated. A derived root manifest records partition paths, counts, schema and
source revisions, byte sizes, and SHA-256 digests. The manifest is atomically
rewritten and can be rebuilt from source files after interruption.

JSONL is the current source format because it is append-friendly, inspectable,
dependency-light, and directly consumable by a later DuckDB mart builder. RM-212
may materialize Parquet only when the measured data shape justifies it; no
database, broker, or new network service is introduced by this ADR.

## Consequences

- PostgreSQL, Outbox/Inbox, RabbitMQ, and the Decision Ledger remain unchanged
  authorities for business state and durable decisions.
- Large records stay outside Git; Git stores code, schemas, evidence, and
  checksums/manifests only.
- Duplicate and malformed records fail explicitly rather than becoming silent
  analytical success.
- The local contract is deterministic and testable, but this checkpoint does
  not claim multi-process file locking, production object storage, or live
  archive delivery. Those concerns require a later evidence-gated task.
