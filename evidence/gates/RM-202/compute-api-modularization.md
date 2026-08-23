# RM-202 Compute API Modularization Evidence

Date: 2026-08-23  
Implementation checkpoint: `145af62` (`refactor(compute): modularize api composition`)  
Remote validation: GitHub Actions run `32625456062`

## Change

- Reduced `services/compute-api/src/routemind_compute/api/app.py` from 817 lines
  to a 30-line composition root.
- Moved immutable request/response schemas to `api/schemas.py` and all FastAPI
  endpoint handlers to `api/routes.py` behind one `APIRouter`.
- Added `api/runtime.py` with an explicit `ComputeRuntime` composition object;
  `create_app()` injects it through `app.state` without adding a network service.
- Preserved all existing health, system, twin control, strategy, dispatch,
  RouteBench, What-if, shadow, and metrics endpoint paths and response models.
- Kept the historical `api.app.REGISTRY` injection point as a compatibility
  bridge for existing failure-injection tests while route execution uses the
  application runtime.

## Local executable evidence

From the repository Compute API gate at checkpoint `145af62`:

- Ruff lint: PASS
- Ruff format check: PASS
- Mypy strict check: PASS (64 source files)
- Contract validator: PASS (5 schemas, 15 fixtures)
- Pytest and coverage: PASS (142 tests, 95.92% total coverage)

## Remote gate

GitHub Actions run `32625456062` completed successfully. All five jobs passed:
Control plane and Compose, Java business runtime, Role-aware web application,
Bounded degradation and resilience, and Python compute and contracts.

## Scope and residual risk

This checkpoint changes module ownership and dependency composition only. The
Compute API remains a single stateless process; no endpoint contract, durable
state authority, solver behavior, or production deployment claim is changed.
