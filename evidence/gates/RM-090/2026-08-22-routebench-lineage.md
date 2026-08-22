# RM-090 RouteBench and Research Lineage Gate

- Time: 2026-08-22T12:58:07+08:00
- Revision before checkpoint: `a35abf08754af730696165991676f425a3a78b32`
- Worktree: RM-090 implementation changes present; no unrelated files
- Boundary: local reduced research fixture; no live provider, production claim, or large dataset

## Commands and results

1. `./scripts/compute-api.ps1 check` - PASS
   - Ruff, format, strict mypy, 4 schemas / 12 fixtures.
   - 40 Python tests passed, including four RouteBench/lineage tests.
   - Total statement/branch coverage: 97.75% (required 95%).
2. `./scripts/full-gate.ps1` - PASS
   - Control plane, Compose, PowerShell syntax, Java 34 tests, Python 40 tests,
     97.75% coverage, contracts, Web static/unit/build gates passed.

## Verified behavior

- `BenchmarkManifest` canonicalizes strategy and metadata ordering while recording
  code version, scenario, seed, load profile, city state, failures, runtime,
  hardware, and dataset provenance.
- `RouteBenchRunner` runs registered strategies through fresh Digital Twin kernels,
  compares assignment metrics, records replay/output digests, and keeps wall-clock
  runtime as an observation excluded from deterministic output hashing.
- `ResearchLineage` records typed hypothesis, observation, result, and conclusion
  nodes with content-derived IDs, parent links, canonical payloads, and queries by
  hypothesis or manifest.

## Evidence limits

This is a reduced local run. It does not claim large-scale throughput, statistical
confidence, calibrated city data, production experiment storage, or RADS behavior.
