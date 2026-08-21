# RouteMind Roadmap

Phases are dependency guides, not permission to remove later capabilities.

## P0 Foundation

Establish repository controls, reproducible local PostgreSQL/RabbitMQ/Redis,
Java and Python service skeletons, versioned contracts, CI, migrations, local
observability, and a verified business-to-compute integration seam.

## P1 Core Domain

Implement customer, merchant, courier, order, and fulfillment aggregates; explicit
state machines; persistence; idempotent APIs; audit trails; optimistic locking;
exceptions; and compensation.

## P2 Distributed and Event Foundation

Implement Outbox relay, RabbitMQ topology, Inbox/deduplication, acknowledgements,
retry, delayed retry, DLQ, poison handling, trace propagation, Redis GEO, and
restart/duplicate/reordering evidence.

## P3 Dispatch Core

Define dispatch contracts and lifecycle, strategy registry, nearest and weighted
greedy baselines, Hungarian assignment, metrics, assignment persistence, and
algorithm comparison.

## P4 Advanced Routing

Add travel providers, road networks, matrices, dynamic travel time, minimum-cost
flow, partitioning, local search, VRP/VRPTW, insertion, and replanning.

## P5 Digital Twin

Implement seeded scenarios, continuous orders, courier movement, merchant
preparation, traffic, replay, manifests, calibration interfaces, and what-if runs.

## P6 Product Surfaces

Deliver role-aware operations, strategy, customer, merchant, and courier workflows
with real-time visualization and accessible operational controls.

## P7 Intelligence

Add Agent Runtime and Orchestrator with safe tools for analysis, SQL/data work,
reports, capacity planning, experiment interpretation, and what-if orchestration.

## P8 Production Engineering

Harden observability, security, resilience, chaos testing, deployment,
backup/recovery, performance, Shadow Mode, staged release, regression detection,
and rollback.

## P9 Research

Implement RADS, RouteBench, lineage, formal baselines, ablations, uncertainty,
counterfactual explanations, switching policies, robustness studies, and
reproducible large-scale experiment packages.
