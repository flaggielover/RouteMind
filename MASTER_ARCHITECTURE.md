# RouteMind Master Architecture

## Architecture style

RouteMind is a modular monorepo with a small number of justified deployables.
Language and process boundaries follow consistency, compute, scaling, and failure
characteristics rather than domain nouns alone.

```text
Role-aware web/mobile surfaces
              |
      API gateway / BFF boundary
              |
  +-----------+------------------+
  |                              |
Java business runtime       Python compute runtime
orders / merchants          dispatch / simulation
couriers / customers        RouteBench / RADS / agents
transactions / Outbox       strategies / analytics
  |            |                 |            |
PostgreSQL   RabbitMQ <-----------+          Redis GEO
                 |
        Inbox + idempotent consumers
                 |
     versioned contracts and trace context
```

## Repository boundaries

```text
services/
  business-api/        Java consistency boundary
  compute-api/         Python dispatch/research boundary
modules/
  domain/              Java domain modules when extracted
  dispatch/            Python algorithms and contracts
  simulation/          Digital Twin and replay
  research/            RADS, RouteBench, lineage
contracts/
  api/                  OpenAPI and compatibility fixtures
  events/               versioned event schemas
apps/
  web/                  role-aware operations/product surfaces
infra/
  compose/              local infrastructure configuration
  observability/        dashboards and collectors
```

Directories appear when their first task requires them; empty architecture theater
is avoided.

## Ownership and data flow

The Java runtime owns authoritative business aggregates and database transactions.
It persists domain changes and Outbox records atomically. A relay publishes events
to RabbitMQ. Python consumers acknowledge only after durable Inbox/deduplication
and processing semantics are satisfied. Dispatch decisions return as versioned,
idempotent commands/events and are validated against current business state.

PostgreSQL schemas are migration-controlled. Service/module ownership must be
explicit before a table is introduced. Redis projections can be rebuilt from
durable state and events.

## Extension contracts

- Dispatch strategies implement a common request/result contract and emit metrics.
- Travel providers support point and matrix operations, time context, capability
  discovery, timeouts, and deterministic fallback.
- Scenarios and experiments use versioned manifests and reproducible seeds.
- Agents use read-oriented tools and bounded commands; policy and audit layers
  mediate any state-changing action.

## Reliability model

Retries are bounded and observable. Idempotency scope and retention are explicit.
Poison events retain diagnostic context in DLQ paths. Correlation propagates over
HTTP, messaging, worker jobs, simulation, and experiments. Dependencies expose
health separately from business readiness. Degradation paths preserve durable
truth and identify reduced service.

## Deployment evolution

P0 uses Docker Compose for infrastructure and local processes for fast iteration.
Modules are extracted into additional services only when independent deployment,
scaling, security, ownership, or failure isolation justifies the operational cost.

See `docs/adr/0001-modular-monorepo-dual-runtime.md` for the initial decision.

## Hardening contracts

Architectural Hardening P20-P23 records the following cross-cutting contracts:

- `WALL`, `SIMULATED`, and `REPLAY` are explicit clock domains. Durable live
  business records use WALL; simulation/replay digests use artifact time and do
  not include wall-clock elapsed duration.
- Java owns a durable assignment lease per courier, with generation/expiry and
  append-only transition evidence. A lease is committed in the same authority
  boundary as the order transition.
- Durable dispatch decisions carry stable identifiers, reference-data identity,
  clock domain, bounded canonical input/output snapshots, and content digests.
- Python solver output is independently verified for dispatch constraints and
  VRPTW route feasibility/objective before crossing the API or experiment
  boundary. The verifier is an executable consistency gate, not a theorem
  prover.
- Determinism is classified per subsystem as critical, configured, or allowed
  operational nondeterminism. Seed, configuration, environment, and repeated
  output digests are recorded by the reproducibility auditor.

The implementation decisions are recorded in ADR-0004 through ADR-0008 and the
phase result in `docs/hardening/HARDENING_CLOSURE_REPORT.md`.
