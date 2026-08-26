# RouteMind Tokyo VM External Validation Design

## Decision

Freeze the VKE diagnostic lane as `EXTERNAL_VKE_VALIDATION = INCONCLUSIVE`,
retain R4-405/R4-406 as `TARGET_PENDING`, and prohibit both target and root-cause
claims from v1/v2/v3. Do not design or run a v4 VKE diagnostic.

Prepare a platform-neutral external qualification on two temporary Vultr Tokyo
VMs. One 32 GiB primary VM runs the actual RouteMind Java/Python workload,
PostgreSQL, RabbitMQ, Redis, two mTLS OpenTelemetry Collector boundaries, and a
self-hosted SigNoz Foundry Compose backend. One 4 GiB recovery VM independently
restores, reconciles, and rolls back a digest-bound synthetic package pulled over
the private VPC. No paid execution is authorized by this design.

## Alternatives

### Single VM

This is the cheapest topology and can prove telemetry export and process-level
failure recovery. It cannot independently separate the source workload host from
the recovery observer, so it weakens the R4-406 failure-domain evidence. Rejected.

### Minimal two VM topology

This retains a distinct recovery execution surface while avoiding Kubernetes,
PVCs, block storage, and load balancers. It is sufficient for every
platform-neutral R4-405/R4-406 acceptance property and keeps cost below a USD 3
incremental ceiling. Selected.

### Three VM topology

Separating the telemetry backend from the workload would add another failure
domain, but R4-405 already requires explicit Collector and backend outage tests.
The additional VM is not needed for the current evidence contract. Rejected as
unnecessary scope.

## Evidence Audit

The original R4-405 acceptance criteria require five-boundary correlation,
tenant-safe cost/cardinality attribution, and durable truth during Collector
failure. The original R4-406 criteria require target PostgreSQL RPO/RTO,
Outbox/Inbox/RabbitMQ/Redis reconciliation, tenant/audit continuity, and rollback.
None requires Kubernetes.

The previous external contract coupled resource usage to Kubernetes Metrics API,
queue durability to PVCs, isolation to NetworkPolicy, and deployment identity to
the VKE control plane. The VM contract replaces those implementation mechanisms
with Docker/cgroup/disk observations, bounded local-disk volumes, internal Docker
networks plus Vultr firewall rules, and credentialed VM/VPC identity. It does not
represent these substitutions as Kubernetes evidence.

The following remain `DEFERRED_VKE`: VKE API/TLS, Kubernetes NetworkPolicy,
Kubernetes Metrics API, PVC/CSI reclaim behavior, pod anti-affinity and worker
failure domains, managed control-plane HA, and Kubernetes rollout/namespace
isolation. VM evidence cannot mark any of them passed.

## Runtime Boundaries

Only TCP 22 is publicly admitted, from the exact operator IPv4 `/32`. A private
TCP 22 VPC rule lets the recovery VM pull an encrypted package from the primary.
RouteMind HTTP, PostgreSQL, RabbitMQ, Redis, OTLP, Collector health, ClickHouse,
and SigNoz ingestion have no host-published ports. SigNoz UI binds loopback and
is accessible only through an SSH tunnel.

Application-to-gateway and gateway-to-backend-ingress OTLP use distinct
execution-scoped mTLS identities. The backend ingress forwards only inside the
isolated SigNoz network. Raw telemetry and recovery data remain in `nrt`; only
leakage-scanned sanitized evidence may leave Tokyo.

The Java and Python containers write real application logs to a bounded shared
volume. Read-only Collector filelog receivers attach service identity and export
those records through the same mTLS path, allowing trace/request correlation
without mounting the Docker socket or publishing a host log port.

## Failure and Recovery

The bounded failure timeline independently stops the RouteMind gateway Collector,
disconnects backend ingress from SigNoz, and stops the SigNoz ingester. Each phase
runs a real synthetic RouteMind workload, checks PostgreSQL durable outcomes, and
then proves queue/export recovery. A failure never authorizes deletion or mutation
of durable business truth.

The primary produces digest-bound PostgreSQL, RabbitMQ, and Redis artifacts. The
recovery VM pulls an encrypted package over the VPC and validates PostgreSQL
restore, RPO/RTO, Outbox/Inbox continuity, RabbitMQ topology/replay, Redis rebuild,
tenant isolation, audit continuity, deliberate mutation, and rollback.

## Safety and Closure

The default action is offline validation. Any provider mutation requires a fresh
Human Gate bound to the canonical contract digest, authenticated quote at or below
USD 3, exact plan/resource validation, and a six-hour timeout. Teardown removes
both Compose projects and volumes, generated secrets, encrypted packages, two VMs,
one VPC, one firewall group, and two firewall rules, then verifies exact 404s and
zero execution-label resources.

A successful future VM run may qualify only platform-neutral R4-405/R4-406 target
properties. It is not production deployment evidence, VKE evidence, or scientific
evidence. R3-325 remains `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

## Human Gate

The exact canonical contract SHA-256 is
`2c6bd381ea8bdbf6a2c91864ec4bbf7589d434b19f043375322138ad7bfc608a`.
Approval must name that digest, the two exact `nrt` VM plans, the six-hour maximum,
the USD 3 incremental ceiling, and contract teardown. No earlier VKE or diagnostic
approval can authorize this execution.
