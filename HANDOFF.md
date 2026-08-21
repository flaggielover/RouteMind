# RouteMind Handoff

Last Known Commit: Current `HEAD`; resolve with `git rev-parse HEAD`

Current Branch: main

Current Phase: P0 Foundation

Current Task: RM-002 - Bootstrap Java business service

Task Status: ready

Completed: Repository reconnaissance found an empty greenfield root and an existing
external data boundary. RM-000 established the authoritative control plane, task
graph validation, quality gates, recovery scripts, architecture contract, and ADR.
RM-001 added pinned PostgreSQL/RabbitMQ/Redis Compose infrastructure, isolated host
ports, health automation, stable RabbitMQ identity, and persistent volumes.

Tests Run: Stage 0 gates passed. RM-001 passed Compose validation, real health,
PostgreSQL SQL, RabbitMQ diagnostics, Redis authenticated ping, loopback binding,
cross-`down/up` persistence for all three services, and the unified infrastructure
gate. Test persistence markers were removed and RouteMind containers stopped.

Known Failures: Maven and Gradle are not installed globally. Repository wrappers
must be used when the Java service is created.

Known Blockers: NONE

Important Context: Keep Java business correctness separate from Python compute and
research. Do not store large datasets or runtime databases in Git. The configured
data boundary is `F:\Projects\RouteMind-Data` on this workstation.

Next Recommended Action: Execute RM-002 by creating a Java business service with a
repository build wrapper, health endpoint, layered module boundaries, Flyway, and
tests against the P0 architecture contract.

Next Candidate Task: RM-002 - Bootstrap Java business service; RM-003 is also ready

Relevant Files: `TASK_GRAPH.yaml`, `MASTER_ARCHITECTURE.md`, `compose.yaml`,
`scripts/full-gate.ps1`, `docs/runbooks/local-development.md`

Do Not Do: Do not collapse the dual runtime, treat Redis as durable truth, bypass
Outbox/Inbox reliability, put large data in Git, or mark tasks passed without gates.
