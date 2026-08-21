# ADR-0001: Modular Monorepo with Dual Runtime

Status: Accepted

Date: 2026-08-21

## Context

RouteMind begins as a greenfield repository but has a broad product and research
target. Durable business correctness, optimization workloads, simulation, and
experimentation have different language and operational strengths. Prematurely
splitting every capability into a service would add failure and transaction costs.

## Decision

Use a modular monorepo. A Java runtime owns durable business aggregates,
transactions, state machines, migrations, and Outbox production. A Python runtime
owns dispatch, optimization, Digital Twin, RouteBench, RADS, analytics, and bounded
agent intelligence. They integrate through versioned HTTP/event contracts.

Begin with one deployable per runtime plus role-aware frontend surfaces. Extract
additional services only for justified deployment, scaling, security, ownership,
or failure-isolation needs.

## Alternatives

- Java only would simplify tooling but weaken the optimization/research ecosystem.
- Python only would speed research but make consistency-sensitive business paths
  less aligned with the intended enterprise backend architecture.
- Fine-grained microservices would encode conceptual boundaries as network failure
  modes before scale or team ownership justifies them.

## Consequences

Cross-runtime contracts and failure semantics must be explicit. Local development
needs both toolchains. Modular boundaries require enforcement inside each runtime.
The approach supports independent evolution without ceremonial services.

## Validation

P0 must prove both runtimes build independently, contracts validate, local
infrastructure is healthy, and a traced integration path works without making
Python authoritative for business state.
