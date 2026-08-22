# RouteMind Handoff

Last Known Commit: Current `HEAD`; resolve with `git rev-parse HEAD`

Current Branch: main

Current Phase: P8 Reliability and Operations

Current Task: RM-090 - Implement RouteBench and research lineage core

Task Status: in_progress

Completed: Repository reconnaissance found an empty greenfield root and an existing
external data boundary. RM-000 established the authoritative control plane, task
graph validation, quality gates, recovery scripts, architecture contract, and ADR.
RM-001 added pinned PostgreSQL/RabbitMQ/Redis Compose infrastructure, isolated host
ports, health automation, stable RabbitMQ identity, and persistent volumes.
RM-002 added the Java 17/Spring Boot 4.1.1 business runtime, Maven Wrapper,
layered module boundaries, health and system endpoints, Flyway, and PostgreSQL
schema ownership.
RM-003 added the Python 3.12-3.14/FastAPI compute runtime, an isolated pinned uv
bootstrap, a hash-bearing lock file, framework-free dispatch strategy contracts,
strict boundary/type/lint gates, and loopback-only health/system endpoints.
RM-004 added independently versioned JSON Schema 2020-12 API/event contracts,
a conservative compatibility policy, positive/negative fixtures, permanent v1
compatibility baselines, and an executable validator in the frozen Python gate.
RM-005 has a least-privilege GitHub Actions workflow with independent control,
Java, and Python/contract jobs. The Python bootstrap is now portable across
Windows and Linux PowerShell.
RM-010 implements sealed customer, merchant, and courier identities, audited
party aggregates, Flyway V2 persistence, and a JPA repository adapter. H2
repository tests and a real PostgreSQL 18.6 migration/constraint probe passed.
RM-011 implements the order lifecycle state machine, immutable transition audit,
JPA persistence, Flyway V3, and optimistic database versioning. Domain and
repository tests plus a real PostgreSQL migration/persistence probe passed.
RM-020 implements the versioned event envelope, transactional order command and
Outbox write, pessimistic claim, stable event IDs, bounded retry, and RabbitMQ
publisher confirms. Flyway V4 and real PostgreSQL/RabbitMQ health/persistence
validation passed.
RM-021 implements durable event-ID deduplication, processing-before-ack
semantics, bounded retries, and observable dead-letter state. Flyway V5 and real
PostgreSQL validation passed.
RM-022 implements durable courier locations, a rebuildable Redis GEO projection,
nearby queries, and explicit `PROJECTED`/`DEGRADED` write outcomes. Flyway V6,
real PostgreSQL/Redis validation, and Redis-outage durability tests passed.
RM-030 implements the versioned Python dispatch result, a replaceable strategy
registry, and a deterministic Haversine nearest baseline with tie-breaking,
latency, and decision metadata.
RM-031 implements weighted-greedy and Hungarian baselines through the same
registry, including rectangular matrix assignment and benchmark provenance.
RM-040 implements point and matrix travel-time provider contracts, a
deterministic local Haversine estimator, and timeout/error fallback with
explicit provider and fallback metadata.
RM-050 implements an immutable seeded scenario manifest, deterministic event
kernel, dispatch/travel integration, replayable state transitions, and a
canonical SHA-256 replay digest.

RM-060 implements the shared React/TypeScript role-aware web surface under
`apps/web`, with Operations, Strategy, Customer, Merchant, and Courier routes,
typed deterministic demo data, independent Java/Python health probes, accessible
responsive controls, a schematic dispatch map, lifecycle timeline, and Playwright
desktop/mobile/axe smoke gates. The surface explicitly labels demo state and does
not own durable business state. Evidence is in
`evidence/gates/RM-060/2026-08-22-role-aware-web.md`.
The RM-060 checkpoint commit `9eaada1` passed all four GitHub Actions jobs in run
`32548856880`.

RM-080 adds bounded request/trace context, structured completion logs, request
count/latency metrics, health/SLI documentation, a Java Micrometer registry-backed
`/metrics` endpoint, Python Prometheus metrics, and deterministic failure injection
for travel-provider and Redis projection degradation. A fixed 100-request local
bounded-burst smoke is included. Local full gate passed with Java 34 tests and
Python 36 tests at 98.07% coverage. Evidence is in
`evidence/gates/RM-080/2026-08-22-observability-resilience.md`.
The RM-080 checkpoint commit `c1913f3` passed all five GitHub Actions jobs in
run `32552399489`, including the focused resilience job.

Tests Run: Stage 0 gates passed. RM-001 passed Compose validation, real health,
PostgreSQL SQL, RabbitMQ diagnostics, Redis authenticated ping, loopback binding,
cross-`down/up` persistence for all three services, and the unified infrastructure
gate. RM-002 passed seven unit, architecture, HTTP, and migration tests; a live
PostgreSQL 18.6 run returned health `UP`, system identity `business-api/java/v1`,
and Flyway history `1:true`. RouteMind processes and containers were stopped.
RM-003 passed Ruff, format, strict mypy, 16 tests with 100% statement/branch
coverage, locked synchronization, and a live Uvicorn HTTP probe. The Python
process was stopped cleanly.
RM-004 validated four schemas and twelve fixtures, including UUID/date-time
formats, dispatch invariants, and stable event/correlation/causation/trace fields.
RM-005 passed all three jobs in GitHub Actions run 32496271644. The first run
caught Windows-specific Java wrapper paths; commit `de5e608` made JDK and wrapper
discovery portable, after which control, Java, and Python/contract jobs passed.
RM-010 passed 18 Java tests, architecture checks, Flyway V2/Hibernate validation
on PostgreSQL 18.6, health `UP`, role-scoped uniqueness, and audit-order checks.
RM-011 passed 22 Java tests, explicit happy/forbidden/repeated/stale command
coverage, Flyway V3/Hibernate validation on PostgreSQL 18.6, and persisted
transition audit rows.
The RM-011 commit `9872d76` passed all three GitHub Actions jobs in run
`32498473119`.
RM-020 passed 27 Java tests, full available gates, Flyway V4/Hibernate
validation on PostgreSQL 18.6, RabbitMQ health via the Compose-mapped port, and
transactional order-to-Outbox persistence.
RM-021 passed 30 Java tests, full available gates, Flyway V5/Hibernate
validation on PostgreSQL 18.6, duplicate suppression, and persisted
`DEAD_LETTER` attempt/error evidence.
RM-022 passed 33 Java tests, full available gates, Flyway V6/Hibernate
validation on PostgreSQL 18.6, authenticated Redis GEOSEARCH, durable courier
location persistence, and degradation behavior when the projection is unavailable.
RM-030 passed the full compute gate: 23 Python tests, strict mypy, Ruff, all
contract fixtures, and 100% statement/branch coverage. The nearest baseline
selects by `(distance_km, courier_id)` and the registry records solve latency,
strategy version, candidate count, and assignment status.
RM-031 passed the full available gate with 26 Python tests and 96.43% total
statement/branch coverage. Weighted-greedy and Hungarian results share the
versioned registry contract; a smoke benchmark records strategy, version,
latency, selected courier, and provenance.
The RM-031 commit `bf44e12` passed all three GitHub Actions jobs in run
`32503389125`.
The RM-030 commit `2a9b3de` passed all three GitHub Actions jobs in run
`32502960806`.
RM-040 passed the full available gate with 29 Python tests and 97.24% total
statement/branch coverage. Point/matrix estimates are deterministic and
primary provider failures or timeouts are marked as fallback results.
RM-050 passed the full available gate with 32 Python tests and 97.92% total
statement/branch coverage. Repeated runs with the same manifest and seed are
byte-identical; changed seed or inputs produce a different replay digest.
The RM-050 commit `595a221` and follow-up baseline coverage commits `ccce5fa`
and `53ab288` passed all three GitHub Actions jobs in run `32505121861`.
The RM-040 commit `cf71191` passed all three GitHub Actions jobs in run
`32504045099`.

Known Failures: Global `JAVA_HOME` points to JDK 8 while the active `PATH` JDK is
17. Repository Java commands deliberately resolve and validate the active JDK.
Maven is not installed globally; use the repository wrapper script.
The first Python dependency sync took several minutes because uv's cache and the
workspace are on filesystems that do not support hardlinks. The script now fixes
copy mode; subsequent frozen syncs are incremental.

Known Blockers: NONE

Important Context: Keep Java business correctness separate from Python compute and
research. Do not store large datasets or runtime databases in Git. The configured
data boundary is `F:\Projects\RouteMind-Data` on this workstation.

Next Recommended Action: Push the RM-080 checkpoint, observe the real GitHub
Actions resilience job, and autonomously fix any CI failure. Then implement
RM-090 RouteBench and research lineage core. Keep web demo state separate from
live business state.

Next Candidate Task: RM-090 - Implement RouteBench and research lineage core

Relevant Files: `TASK_GRAPH.yaml`, `MASTER_ARCHITECTURE.md`, `compose.yaml`,
`scripts/full-gate.ps1`, `scripts/business-api.ps1`,
`scripts/compute-api.ps1`, `services/business-api/README.md`,
`services/compute-api/README.md`, `contracts/README.md`,
`docs/runbooks/local-development.md`

Do Not Do: Do not collapse the dual runtime, treat Redis as durable truth, bypass
Outbox/Inbox reliability, put large data in Git, or mark tasks passed without gates.
