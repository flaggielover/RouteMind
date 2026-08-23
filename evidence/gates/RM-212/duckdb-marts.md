# RM-212 DuckDB Marts Evidence

Date: 2026-08-23  
Implementation checkpoint: `5f1cccf`
Engine: DuckDB `1.5.5`, pinned in `pyproject.toml` and `uv.lock`

## Changed

- Added `AnalyticalMartBuilder` with full and incremental modes.
- Added manifest SHA-256 verification before load and parameterized inserts.
- Added `fact_event`, six curated fact views, and the justified
  `dim_strategy` dimension.
- Added logical source/content digests and explicit build counters.
- Added a repository-local F-drive uv cache path under ignored `.tools/` so the
  full C drive cannot block the reproducible dependency workflow.
- Added `scripts/analytics_mart_gate.py` to the normal Compute check.

## Local gate

Command: `./scripts/compute-api.ps1 -Action check`

- Ruff check/format: PASS
- mypy strict: PASS
- Contract fixtures: PASS (5 schemas, 15 fixtures)
- Python tests: PASS (174 tests)
- Coverage: PASS (95.47%, threshold 95%)
- Determinism gate: PASS
- Archive gate: PASS
- Mart tests: PASS for full rebuild, stable logical digest, incremental
  idempotency/new records, missing manifest, invalid mode, and digest mismatch
- GitHub Actions `32643098647`: PASS across all five jobs, including Linux
  Python/DuckDB and browser smoke

## Boundaries

The evidence is local and fixture-sized. It does not claim production query
latency, concurrent writers, scheduled ingestion, Parquet performance, or
warehouse-scale capacity. Marts are read models and do not own business state.
