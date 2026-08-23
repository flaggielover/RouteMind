# RM-211 Analytical Archive Evidence

Date: 2026-08-23  
Implementation checkpoint: pending commit after local validation  
Owner: Python compute/analytics boundary  
Data root: `ROUTEMIND_DATA_ROOT` (tests use an isolated temporary directory)

## Changed

- Added `AnalyticalArchive` and `AnalyticalRecord` in
  `services/compute-api/src/routemind_compute/application/analytics_archive.py`.
- Added partitioned append-only JSONL storage, canonical serialization,
  duplicate ID rejection, atomic derived manifest rebuild, and integrity scan.
- Added unit tests covering root configuration, provenance, partitioning,
  duplicate rejection across partitions, rebuild/verify, unsafe values, and
  corrupt lines.
- Added `scripts/analytics_archive_gate.py` and invoked it from
  `scripts/compute-api.ps1 -Action check`.
- Recorded the boundary decision in ADR-0009.

## Local gate

Command: `./scripts/compute-api.ps1 -Action check`

- Ruff check: PASS
- Ruff format: PASS
- mypy strict: PASS
- Contract fixtures: PASS (5 schemas, 15 fixtures)
- Python tests: PASS (168 tests)
- Coverage: PASS (95.66%, threshold 95%)
- Determinism gate: PASS; seeded replay digest stable
- Analytical archive gate: PASS

Archive gate output:

```json
{"duplicate_rejected": true, "manifest_version": "v1", "partition_count": 1, "record_count": 2, "unique_record_ids": 2, "valid": true}
```

## Boundaries

This evidence proves the local archive contract only. It does not claim
multi-process locking, production object storage, Parquet materialization,
live event delivery, or production retention/compliance. RM-212 owns the
reproducible DuckDB mart decision.
