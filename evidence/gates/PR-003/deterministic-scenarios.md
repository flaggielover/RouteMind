# PR-003 Deterministic Scenario Evidence

Date: 2026-08-30  
Scope: local simulation/replay only; no external operation or scientific claim.

## Commands

- `python scripts/deterministic_scenarios.py --list`
- `uv run --project services/compute-api python scripts/deterministic_scenarios_test.py`
- `uv run --project services/compute-api python scripts/deterministic_scenarios.py --seed 17`
- `uv run --project services/compute-api ruff check scripts/deterministic_scenarios.py scripts/deterministic_scenarios_test.py`
- `uv run --project services/compute-api ruff format --check scripts/deterministic_scenarios.py scripts/deterministic_scenarios_test.py`
- `git diff --check`

## Results

- The catalog lists exactly `NORMAL_BASELINE`, `DINNER_RUSH`,
  `COURIER_SHORTAGE`, `MERCHANT_DELAY`, `TRAFFIC_DEGRADATION`,
  `ROUTING_PROVIDER_FAILURE`, `DISPATCH_PRESSURE`, and `RECOVERY`.
- Four focused tests pass. All eight scenarios run through the existing
  `ScenarioManifest`/`ScenarioKernel` interface with a pinned seed and repeated
  replay digest verification.
- Representative behavior is explicit: dinner demand is larger than baseline,
  courier shortage and dispatch pressure retain unassigned outcomes, routing
  provider failure uses the existing bounded local fallback, and recovery verifies
  replay of the same manifest. No process restart or external provider behavior is
  implied by the `RECOVERY` result.
- `--list` works with repository Python because it does not import compute
  dependencies; execution tests run under the pinned compute `uv` environment.
- Ruff, formatting, and `git diff --check`: PASS.

## Remote CI

- PR-002 implementation `9671126b1e983a9b6ddeaa3ce075041d677de84c`:
  Actions run `33299312559`, all five jobs successful.

This evidence qualifies deterministic local scenario setup and replay only. It is
not a production, external-provider, performance, or scientific claim.
