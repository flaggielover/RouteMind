# RouteMind Round 2 Gap Audit

- Date: 2026-08-22 (Asia/Shanghai)
- Baseline revision: `cd0f999`
- Scope: `MASTER_SPEC.md`, `MASTER_ARCHITECTURE.md`, `ROADMAP.md`, executable
  source, tests, browser smoke, and Round 1 evidence

## Executive summary

Round 1 is a healthy architectural baseline: the Java/Python split, durable
domain primitives, Outbox/Inbox contracts, Redis GEO projection, dispatch
baselines, travel fallback, Digital Twin kernel, RouteBench, RADS, security
boundaries, and CI gates are executable locally and in GitHub Actions. They do
not yet constitute a live urban delivery product. The web application consumes
one deterministic snapshot, the Java service exposes only system/metrics
endpoints, the Python service exposes only health/system endpoints, and several
visible controls are decorative.

Round 2 therefore starts from `28 / 28` Round 1 tasks passed and adds a separate
dependency graph. Round 1 statuses and history are preserved.

## Capability classification

| Capability | Classification | Evidence and gap |
| --- | --- | --- |
| Java durable party/order state | FULL for current aggregates | JPA/Flyway/domain tests and PostgreSQL evidence exist; no product-facing read/command API is wired. |
| Transactional Outbox/Inbox and broker contracts | PARTIAL | Durable primitives and unit/integration evidence exist; no browser-to-business-to-compute golden path exists. |
| Python dispatch registry and baselines | BASELINE_ONLY | Nearest, weighted-greedy, and Hungarian are reproducible; no HTTP dispatch command/snapshot endpoint or operational assignment persistence exists. |
| Travel provider abstraction | BASELINE_ONLY | Deterministic Haversine and fallback contracts exist; no network/zone graph, dynamic incidents, or live route geometry exists. |
| Digital Twin | BASELINE_ONLY | Seeded finite scenario kernel and replay digest exist; no continuous clock, courier motion, preparation queue, demand stream, traffic UI, or pause/resume controls exist. |
| RouteBench/RADS/lineage | FULL for reduced local research baseline | Recorded experiments are reproducible; product integration and large-scale campaigns remain later work. |
| Authentication, authorization, input/rate/deployment boundaries | BOUNDARY_ONLY | Fail-closed policies are locally executable; provider identity, WAF, distributed counters, and production deployment enforcement remain external. |
| Web data source | DEMO_ONLY | `demoDataSource` is the default and supplies fixed orders, couriers, merchants, metrics, and timestamps. |
| Web service health | PARTIAL | Health probes are real HTTP requests, but product state is not sourced from either service and failure is not propagated to views. |
| Real-time updates | MISSING | No SSE/WebSocket endpoint, event cursor, reconnect behavior, stale-state handling, or browser event stream exists. |
| Operations command center | DEMO_ONLY | Operations view has a schematic x/y map, fixed snapshot, and selection only; filter, details, activity, alerts, imbalance, and route inspection are absent or decorative. |
| Real map/geospatial view | MISSING | `OperationsMap` renders a schematic coordinate surface; no provider-neutral map/tile/routing adapter or explicit local geospatial fallback exists. |
| Customer workflow | DEMO_ONLY | Customer route renders a completed fixture; create/order tracking/help actions do not call a service. |
| Merchant workflow | DEMO_ONLY | Merchant queue is fixture data; `Mark ready` has no command path. |
| Courier workflow | DEMO_ONLY | Courier shift and route are fixture data; `Open route` and task actions have no command path. |
| Advanced dispatch | BASELINE_ONLY | No capacity/preparation-aware scoring, min-cost flow/partitioning, VRP/VRPTW, dynamic insertion, or replanning implementation. |
| Strategy Laboratory | DEMO_ONLY | Strategy rows and scores are hard-coded display values; no registry API, parameter schema, execution, provenance, or result visualization. |
| Shadow Mode product surface | BOUNDARY_ONLY | Python decision contract and regression gate exist; no active/candidate comparison UI or promotion gate workflow. |
| End-to-end delivery | MISSING | Existing browser tests explicitly render demo state; no real PostgreSQL/RabbitMQ/Redis/service-process golden path. |
| Failure/degradation product behavior | PARTIAL | Local resilience/failure injection gates exist; role surfaces do not show bounded degradation or stale live state. |
| UX/accessibility/mobile | BASELINE_ONLY | Responsive and axe smoke gates pass for static pages; product workflows, loading/empty/error states, drawers, forms, and mobile actions are shallow. |
| Data-root artifact boundary | BOUNDARY_ONLY | Policy is documented; Round 2 simulation/matrix/replay adapters must use `ROUTEMIND_DATA_ROOT` without committing large artifacts. |

## Work mapping

- Live path and modes: RM-100 through RM-108.
- Operations command center and geospatial productization: RM-110 through RM-114.
- Customer, merchant, courier, mobile, and degraded command workflows: RM-120 through RM-124.
- Advanced dispatch portfolio: RM-130 through RM-136.
- Dynamic travel/network model: RM-140 through RM-143.
- Living Digital Twin, replay, and What-if: RM-150 through RM-158.
- Functional Strategy Laboratory and Shadow Mode: RM-160 through RM-163.
- Real local E2E, failure E2E, performance, UX closure, and adversarial Round 2 audit: RM-170 through RM-190.

## Assumptions for the first implementation slice

1. Java remains the source of durable business snapshots and commands.
2. Python remains the source of dispatch/simulation/experiment computations.
3. The web client receives an explicit `LIVE`, `DEMO`, or `REPLAY` source state;
   it never silently falls back from live data to fixtures.
4. SSE is the initial browser push mechanism because it is one-way, naturally
   reconnectable, and matches the current event publication direction. A later
   task may justify WebSocket if bidirectional needs are demonstrated.
5. Empty live state is a valid, visible state. Fixtures remain available for
   offline/browser tests and are labeled as demo data.

## Evidence boundary

This audit does not claim live-provider, production-map, production-identity,
large-scale performance, or production rollback validation. Those remain
explicit Round 2 tasks or deferred external gates.
