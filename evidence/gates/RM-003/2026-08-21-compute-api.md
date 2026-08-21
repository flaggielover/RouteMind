# RM-003 Python Compute Service Gate Evidence

Date: 2026-08-21 Asia/Shanghai

Revision: Worktree based on `ac2e284`; the exact RM-003 checkpoint is the commit
containing this evidence file.

## Reproducible toolchain

Official PyPI metadata was checked on 2026-08-21 for Python 3.14 compatibility.
The project supports Python `>=3.12,<3.15`, pins direct runtime and development
dependencies, and commits uv's transitive lock with artifact hashes.

```text
Python: 3.14.6
uv: 0.12.5 (isolated repository bootstrap)
FastAPI: 0.141.1
Pydantic: 2.13.4
Uvicorn: 0.52.4
Starlette test transport: httpx2 2.12.0
uv sync --frozen: PASS (31 installed packages)
```

`scripts/compute-api.ps1` validates Python, bootstraps exactly uv 0.12.5 under
the ignored `.tools` directory, forces copy mode for this cross-filesystem
workspace, and runs all project commands with `--frozen` except the explicit
lock maintenance action.

## Static, type, and test gates

```text
ruff check .: PASS
ruff format --check .: PASS
mypy src tests (strict): PASS, 0 issues in 12 source files
pytest: PASS, 16 tests
statement coverage: 100%
branch coverage: 100%
scripts/full-gate.ps1: PASS (control plane, Java regression, Python gates)
```

Tests cover immutable dispatch values and invariants, the runtime-checkable
strategy protocol, standard-library-only domain imports, inward dependency
rules, health/system HTTP responses, and process entry-point configuration.

## Live HTTP gate

The installed entry point started a real Uvicorn process from the frozen
environment.

```text
Listen address: 127.0.0.1:18081
GET /healthz: 200, status=UP
GET /api/v1/system: 200
service=compute-api
runtime=python
architecture_version=v1
durable_state_owner=false
```

The server completed application shutdown after both probes. No database,
message broker, or cache client exists in the compute package or its dependency
declarations.

## Defects caught during validation

- The first uv version check compared build metadata as part of the semantic
  version and unnecessarily recreated its tool environment. It now compares
  only the version token.
- Cross-filesystem hardlinks were unavailable, so uv now uses explicit copy mode
  instead of probing and warning on every sync.
- Starlette deprecated its old `httpx` test transport in favor of `httpx2`; the
  locked development dependency follows the current Starlette contract.
- The coverage gate initially stopped at 80%; entry-point and invariant branches
  were added until both statement and branch coverage reached 100%.
