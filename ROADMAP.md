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

## Round 2 Productization and Living Digital Twin

Round 1 closure is not product completion. Round 2 extends the graph from
RM-100 through RM-190 in dependency-ordered slices:

- P10 live/demo/replay data modes, Java read/command APIs, Python dispatch API,
  SSE updates, reconnect semantics, and activity projection;
- P11 operations command center, real geospatial map adapter/fallback, filters,
  entity drawers, exceptions, imbalance, and alerts;
- P12 real customer, merchant, courier, degraded, and mobile workflows;
- P13 constrained dispatch, risk/preparation/capacity scoring, flow, VRP/VRPTW,
  insertion, replanning, and durable dispatch integration;
- P14 dynamic network travel, data-root matrices, traffic, and incidents;
- P15 continuous Digital Twin, demand, courier motion, merchant preparation,
  traffic perturbations, control API, UI, replay, and What-if;
- P16 functional Strategy Laboratory, experiment provenance, comparisons, and
  Shadow Mode productization;
- P17-P19 real local E2E, failure E2E, measured performance, UX closure, and
  adversarial evidence audit.

Large maps, matrices, replay archives, and experiment outputs remain under
`ROUTEMIND_DATA_ROOT`; production map providers, identity, WAF, and full-scale
compute remain explicit external gates unless exercised with matching evidence.
