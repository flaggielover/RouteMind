# RouteMind Master Specification

## Mission

RouteMind is a production-minded urban delivery platform and reproducible research
environment. It must support reliable business execution, real-time strategy
evaluation, urban delivery simulation, and defensible experimentation without
making research code responsible for transactional correctness.

## Product and domain capabilities

The durable domain covers customers, merchants, couriers, orders, fulfillment,
dispatch, exceptions, and compensation. Lifecycles use explicit state machines,
transactional boundaries, idempotent commands, optimistic concurrency where
appropriate, and auditable transitions.

The product surface must eventually expose an operations command screen, strategy
laboratory, and customer, merchant, and courier workflows. Shared components and
role-aware applications are preferred to duplicate frontends.

## Distributed foundation

RabbitMQ is the durable integration broker. Producers use transactional Outbox and
stable event, correlation, causation, and trace identifiers. Consumers explicitly
acknowledge, deduplicate through Inbox/idempotency records, retry with bounded
backoff, route poison messages to dead-letter queues, and expose failures.

Redis supports GEO courier indexing, hot dispatch state, caching, and carefully
justified coordination. PostgreSQL remains durable truth.

## Dispatch and travel

Dispatch is strategy-pluggable. Planned baselines and extensions include nearest
neighbor, weighted greedy, Hungarian assignment, minimum-cost flow, batched and
partitioned assignment, local search, VRP/VRPTW, dynamic insertion, and replanning.
Strategies account progressively for capacity, merchant preparation, courier
motion, continuous arrivals, travel-time changes, service balance, and risk.

A formal travel-model interface supplies distance and travel time over coordinates
or road networks, supports matrix/batch calls and dynamic updates, and has
deterministic local fallbacks. Paid map credentials cannot block core development.

## Digital Twin and strategy control

The Digital Twin represents orders, merchants, customers, couriers, roads, travel
time, traffic, preparation delays, demand, capacity, and dispatch decisions. It
supports seeded simulation, replay, scenario manifests, what-if experiments, and
eventual calibration against observed data.

The Strategy Control Center registers and versions strategies, validates parameter
schemas, compares runs, supports replay and Shadow Mode, and later enables staged
release, regression detection, and rollback.

## Research systems

RADS, the Risk-aware Adaptive Dispatch System, is a measurable subsystem composed
of state encoding, risk/uncertainty representation, strategy selection or mixture,
multi-objective evaluation, and counterfactual explanation. Claims require
experiments, baselines, and ablations.

RouteBench records algorithm, strategy, scenario, load, city state, failures,
configuration, code version, dataset provenance, seed, hardware when relevant, and
results. Metrics include latency, overtime, completion, distance, utilization,
fairness, cost, throughput, compute overhead, switching, and robustness.

Research lineage connects hypothesis, manifest, code version, data/scenario, seed,
result, analysis, and conclusion. Hypotheses, observations, empirical results,
mathematical claims, and production claims remain explicitly distinct.

## Intelligence boundary

The Agent Orchestrator and Agent Runtime may provide operations diagnosis,
explanations, reporting, SQL/data analysis, capacity planning, strategy analysis,
experiment interpretation, what-if orchestration, discovery, and chaos analysis.
Deterministic domain and optimization systems retain operational authority.

## Operational qualities

The platform must mature toward explicit timeout, retry, circuit breaker, fallback,
graceful degradation, health checks, isolation, observability, human intervention,
and rollback behavior. Security includes authentication, authorization, input
validation, rate limiting, secret isolation, dependency/container hygiene, SBOM,
provenance, and auditability in proportion to risk.

Database changes use migrations, constraints, justified indexes, compatibility
analysis, and recovery thinking. Concurrency tests cover duplicate, stale,
reordered, retried, concurrent, and crash-recovery behavior.

## Completion semantics

Every capability is labeled accurately as planned, implemented, locally verified,
live verified, or production verified. Significant work passes its required gates
and links executable evidence before `TASK_GRAPH.yaml` marks it `passed`.
