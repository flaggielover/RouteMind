# RM-158 What-if Scenario Comparison

Date: 2026-08-23

## Implemented boundary

- Python adds a pure, bounded `WhatIfRunner` that derives immutable demand,
  supply, preparation, traffic, strategy, and risk variants from one recorded
  scenario manifest and executes each through the existing `ScenarioKernel`
  and registered strategy boundary.
- `POST /api/v1/experiments/what-if` returns baseline and variant metrics with
  assignment rate, simulated duration, scenario-risk index, replay digest,
  manifest digest, output digest, and comparison digest. Bounds and unknown
  strategies fail explicitly; no durable state is mutated.
- The Strategy surface now exposes the variant controls and renders compact
  baseline/variant metrics with recorded-run provenance. The copy explicitly
  says `scenario comparison; not a causal production claim`; API failures and
  clear/idle states remain visible.

## Evidence

- Compute check passes 142 Python tests at 95.88% coverage, Ruff, format, mypy,
  and 5 schemas/15 contract fixtures. `test_what_if.py` covers deterministic
  repeated runs, every variant dimension, bounds, duplicate/reserved ids,
  unknown strategies, API success, and explicit API failures.
- Web check passes 13 test files and 47 tests, plus Prettier, ESLint, TypeScript,
  and production build. The adapter test verifies bounded request serialization
  and response provenance mapping; component tests cover run, clear, and error
  states.
- `./scripts/web.ps1 -Action e2e` passes 23 desktop/mobile browser tests with
  one existing desktop-only skip. The new Strategy test mocks the compute API,
  runs the comparison, checks baseline/variant metrics, recorded-run provenance,
  and the non-causal claim label on both viewports. Existing role, simulation,
  replay, responsive, and axe tests remain green.
- `./scripts/full-gate.ps1` passes Java 60 tests, Python 142 tests at 95.88%,
  Web 47 unit tests/build, and 5 schemas/15 fixtures.

## Gate decision

Local L6 What-if and L4 What-if browser evidence is complete. GitHub Actions run
`32607641909` passed all five jobs, including the Python compute and Web browser
smoke gates. RM-158 is fully validated.
