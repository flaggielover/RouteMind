# RouteMind

RouteMind is an evidence-driven urban delivery platform and research system. It
combines a consistency-focused Java business backend with Python dispatch,
simulation, optimization, benchmarking, and intelligence modules.

The repository is currently in **P0 Foundation**. The authoritative project
state lives in the root control files, especially `TASK_GRAPH.yaml`,
`PROGRESS.md`, and `HANDOFF.md`.

## Resume work

From PowerShell:

```powershell
./scripts/resume.ps1
```

Run the fast repository gate:

```powershell
./scripts/verify.ps1
```

Inspect local prerequisites:

```powershell
./scripts/doctor.ps1
```

Start the local platform dependencies:

```powershell
./scripts/infra.ps1 up
```

Build or run the durable Java business service:

```powershell
./scripts/business-api.ps1 test
./scripts/business-api.ps1 run
```

Validate or run the stateless Python compute service:

```powershell
./scripts/compute-api.ps1 check
./scripts/compute-api.ps1 run
```

This exposes PostgreSQL on `127.0.0.1:15432`, RabbitMQ AMQP on
`127.0.0.1:15673`, RabbitMQ Management on `http://127.0.0.1:15674`, and Redis on
`127.0.0.1:16379` by default. Local credentials come from `.env` or the safe
development placeholders in `.env.example`; they are not production defaults.

Large datasets and generated research artifacts belong in the external data
boundary configured by `ROUTEMIND_DATA_ROOT`, not in Git.

## Architecture

- `services/`: deployable business and compute services.
- `modules/`: reusable domain, dispatch, simulation, and research modules.
- `contracts/`: versioned APIs, messages, schemas, and compatibility fixtures.
- `apps/`: maintainable multi-end product surfaces.
- `infra/`: local and deployment infrastructure.
- `docs/`: architecture, ADRs, APIs, research, and runbooks.
- `evidence/`: lightweight committed gate and experiment evidence.

See `MASTER_SPEC.md` and `MASTER_ARCHITECTURE.md` before implementation.
