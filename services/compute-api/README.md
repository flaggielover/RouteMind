# RouteMind Compute API

This Python runtime owns stateless dispatch computation, optimization,
simulation, benchmarking, and research workloads. It never owns durable business
state or transactional lifecycle decisions.

## Boundaries

- `domain`: immutable compute inputs, outputs, and strategy protocols; standard
  library only.
- `application`: compute orchestration; may depend on domain only.
- `api`: inbound HTTP adapter; may depend on application and domain.
- `infrastructure`: external compute adapters; never an authoritative data store.

Boundary tests inspect imports and reject inward dependencies on frameworks,
databases, brokers, and caches.

## Commands

From the repository root:

```powershell
./scripts/compute-api.ps1 lock
./scripts/compute-api.ps1 check
./scripts/compute-api.ps1 run
```

The script pins `uv` in an ignored, isolated tool environment. `uv.lock` is the
reproducible dependency source. The service listens on `127.0.0.1:18081` by
default.
