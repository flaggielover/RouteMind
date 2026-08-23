# RouteMind Enhancement Architecture Audit

Date: 2026-08-23  
Audit checkpoint: `5fc2b5b`  
Hardening baseline: `370ef90`  
Repository: `flaggielover/RouteMind` (`main`)

## Purpose and method

This is a read-oriented RM-210 audit of the actual RouteMind source tree after
Architectural Hardening. It classifies the Enhancement Pass inventory before
implementation and creates the dependency-ordered RM-211 through RM-236 work
packages. The audit does not call a demo surface production, does not add a
network service, and does not move large data into Git.

The evidence reviewed includes the Java business runtime under
`services/business-api`, the Python compute/runtime and tests under
`services/compute-api`, the role-aware React surface under `apps/web`, versioned
contracts under `contracts`, the hardening closure report, and the existing
Round 2 evidence gates. The repository control plane validates the graph with
`python scripts/validate_control_plane.py`.

## Authority and boundary decisions

| Area | Owner | Existing evidence | Enhancement rule |
| --- | --- | --- | --- |
| Durable business state, lifecycle, commands, leases, ledger | Java + PostgreSQL | Java domain/application packages, Flyway V1-V12, RM-204/RM-205 gates | New business truth remains Java-owned and migration-controlled |
| Events and integration | Java Outbox/Inbox + RabbitMQ | Existing Outbox/Inbox tests and RM-020/RM-021 evidence | Archives consume versioned events; they do not replace Outbox or Inbox |
| Hot location projection and candidate lookup | Redis GEO | Courier location store, projection/degradation tests, RM-022 evidence | Redis remains rebuildable and bounded; durable history is selective |
| Dispatch, simulation, optimization, ETA, analytics, experiments | Python compute | `application/` modules, strategy registry, Twin, RouteBench, RADS tests | Compute returns versioned results and never commits business state |
| Presentation and interaction | React/TypeScript web | `apps/web/src`, role routes, map/replay/What-if/strategy components | UI consumes typed snapshots and explicit LIVE/DEMO/REPLAY/SIMULATION modes |
| Large analytical data and experiment artifacts | `ROUTEMIND_DATA_ROOT` | External `F:\Projects\RouteMind-Data` boundary in control docs | Git stores schemas/manifests/checksums, not large event or map payloads |

## Capability classification

| RM task | Capability | Classification | Current evidence | Planned owner / dependency |
| --- | --- | --- | --- | --- |
| RM-211 | Append-only analytical event/decision archive | ABSENT | No committed archive writer or manifest contract exists | Python archive adapter; RM-210 |
| RM-212 | DuckDB analytical marts | ABSENT | No DuckDB dependency or reproducible mart command exists | Python analytics; RM-211 |
| RM-213 | Semantic metrics layer | PARTIAL | Java Micrometer/Python Prometheus and UI metric cells exist, but no shared definitions/marts | Python analytical contract; RM-212 |
| RM-214 | End-to-end OpenTelemetry tracing | PARTIAL | Request/trace context and structured metrics exist; exporter/span bridge is absent | Java/Python/Web boundary adapters; RM-210 |
| RM-215 | Reconciliation and invariant drift | ABSENT | Durable invariants are tested at command boundaries, but no continuous detector/status model exists | Java detector plus analytical evidence; RM-211/RM-214 |
| RM-216 | Fulfillment saga expansion | PARTIAL | Order lifecycle and merchant preparation exist; bounded courier/pickup/delivery exception saga is incomplete | Java state machine; RM-210 |
| RM-217 | Live courier location streaming/history | PARTIAL | Java location persistence, Redis projection, and SSE exist; sequence-rich bounded history/consumer contract is incomplete | Java + Redis/SSE; RM-216 |
| RM-218 | Location integrity/hotspots | ABSENT | Motion and location primitives exist, but no integrity state or privacy-bounded hotspot mart | Python analytics + Web; RM-217 |
| RM-219 | ETA foundation | PARTIAL | Travel and merchant preparation estimates exist; no unified prediction/outcome record | Python compute + Java read model; RM-216 |
| RM-220 | ETA calibration/SLA risk | ABSENT | No interval calibration or evidence-gated risk thresholds | Python analytics; RM-219 |
| RM-221 | Delay attribution | ABSENT | Lifecycle timestamps exist but no reconciled accounting waterfall | Python analytical mart; RM-219/RM-220 |
| RM-222 | Multi-city geo foundation | PARTIAL | Provider-neutral map adapter and deterministic demo map exist; no multi-city aggregate contract | Web + Python analytical layer; RM-210/RM-211 |
| RM-223 | City/zone drilldown | PARTIAL | Operations map and filters exist; zoom-aware aggregation and zone semantics are thin | Web; RM-222 |
| RM-224 | Arc/flow visualization | ABSENT | No data-backed arc/flow view is committed | Web consuming archive/marts; RM-211/RM-223 |
| RM-225 | Geo analytical layers | PARTIAL | Map mode and entity layers exist; analytical heat/risk/supply layers and legends are incomplete | Web + semantic metrics; RM-223/RM-224 |
| RM-226 | Decision X-Ray | PARTIAL | Durable Decision Ledger and solver verifier exist; no read-only inspection surface/replay view | Java read API + Web; RM-205/RM-206 |
| RM-227 | Strategy analytics/Pareto | PARTIAL | Strategy registry, comparison, Shadow and What-if components exist; shared metric/Pareto computation is incomplete | Python + Web; RM-213/RM-226 |
| RM-228 | Digital Twin visualization center | PARTIAL | Twin control, replay, simulation panels and timeline exist; no unified evidence-oriented center | Python + Web; RM-210/RM-211 |
| RM-229 | What-if delta visualization | PARTIAL | Perturbation and What-if APIs/components exist; evidence-linked multi-delta view is thin | Python + Web; RM-226/RM-228 |
| RM-230 | Reliability Center | PARTIAL | Resilience gates, failure injection, and health/metrics exist; no consolidated operator surface | Web + trace/reconciliation data; RM-214/RM-215 |
| RM-231 | Research Center | PARTIAL | RouteBench, RADS, lineage, manifests and strategy panels exist; no unified read-only research surface | Python + Web; RM-212/RM-213/RM-228 |
| RM-232 | Agent analytical substrate | PARTIAL | Agent Runtime has bounded tools/audit/fallbacks; analytical evidence tools are not present | Python agent boundary; RM-213/RM-226/RM-231 |
| RM-233 | Reference-data versioning | PARTIAL | Decision Ledger stores reference identity, but no general immutable registry/version API | Java contract + archive; RM-205/RM-211 |
| RM-234 | Event upcasting/replay compatibility | ABSENT | Event schemas are versioned, but historical upcasters and compatibility replay gate are absent | Contract/replay boundary; RM-203/RM-233 |
| RM-235 | Enhancement E2E/adversarial validation | ABSENT | Round 2 adversarial gates exist; Enhancement cross-layer journey does not | Cross-stack; all material Enhancement tasks |
| RM-236 | Enhancement closure + Round 3 graph | ABSENT | Hardening closure and Round 3 gap prose exist; Enhancement closure/report and research graph do not | Control plane; RM-235 |

## Dependency graph rationale

The graph intentionally establishes provenance before visualization: RM-211
archive precedes marts and metrics; metrics and evidence precede Reliability,
Research, Agent, and Strategy surfaces; the durable ledger precedes Decision
X-Ray and What-if deltas; location and fulfillment contracts precede ETA and
delay accounting; geo aggregation precedes arcs and layers. RM-235 is the only
cross-cutting validation task and RM-236 is the closure gate. No task introduces
Kafka, Spark, Hadoop, ClickHouse, Elasticsearch, or an unjustified deployable.

## Maturity and explicit deferrals

The Enhancement Pass may produce `BASELINE`, `ENGINEERING`, `DEMO`, or
`PRODUCTION-CANDIDATE` artifacts only when their evidence supports the label.
It must not claim production deployment, external travel-provider validation,
scientific novelty, causal inference, calibrated ETA, or nationwide operation
without matching data and gates. Round 3 research remains a prepared task graph
after RM-236; it is not launched by this audit.

## RM-210 acceptance evidence

- The actual repository structure and existing evidence were classified above.
- Java/Python/Web/data-root authority boundaries are explicit.
- RM-211 through RM-236 are present in `TASK_GRAPH.yaml` with dependency edges,
  acceptance criteria, gates, evidence paths, and truthful initial states.
- Control-plane validation passes at this checkpoint; no product behavior is
  changed by the audit.
