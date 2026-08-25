# ADR 0033: Vultr Tokyo Deployment Target

- Status: Accepted
- Date: 2026-08-25
- Decision owner: RouteMind owner
- Task: R4-401

## Context

Round 4 requires a real target before telemetry, recovery, capacity, chaos, and
staged-release evidence can be interpreted. The repository previously had only
loopback Docker Compose evidence and deliberately made no production claim.

The owner explicitly approved Vultr in Tokyo, Japan as RouteMind's current
target platform and data-residency region. That approval selects a target. It
does not provide credentials, authorize spend, create resources, or prove a
production deployment.

## Decision

The target region is Vultr `nrt` (Tokyo, Japan). The initial candidate topology
uses one high-availability VKE control plane, three `vhp-4c-8gb-amd` worker
nodes, a Vultr Load Balancer, independent Block Storage volumes, and a separate
Tokyo backup host. Java and PostgreSQL remain authoritative for durable
business state. Python remains responsible for optimization, simulation,
research, and bounded analytical work. RabbitMQ remains the reliable event
backbone and Redis remains rebuildable hot state.

All production/customer payloads, tenant events, courier trajectories,
application telemetry, research artifacts, and recovery payloads must remain in
Tokyo. GitHub may hold source, CI metadata, and synthetic fixtures, but not
production/customer payloads. Provider automatic backups remain disabled until
their storage location is contractually verified.

The initial monthly public-catalog estimate is USD 239, with a USD 61 planning
contingency and a USD 300 ceiling. This is a planning bound, not spend approval.
An authenticated Tokyo quote, quota check, credentials, and explicit resource
creation/spend approval are required before provisioning.

The target is deliberately single-region. VKE control-plane and worker-node
redundancy mitigate narrower failures but do not establish independent Tokyo
availability zones or regional disaster recovery. Region-wide RPO and RTO are
therefore uncommitted in v1. R4-406 must validate only the recorded in-region
PostgreSQL RPO of 15 minutes and RTO of 120 minutes. R4-407 must qualify the
capacity and SLO assumptions before they can support a production-candidate
label.

## Consequences

- R4-405 and R4-406 may begin only after R4-401 closes.
- Any real Vultr action requires out-of-band credentials and separate approval.
- The initial 99.5% monthly API availability objective reflects the accepted
  single-region risk and carries a 216-minute 30-day error budget.
- Local RM-180 performance remains loopback regression evidence and is not
  carried forward as production capacity.
- Round 3 scientific outcomes, including frozen R3-325, are unaffected.

The executable contract is
`contracts/deployment/r4-401-vultr-tokyo-v1.json`. The public provider evidence
snapshot is
`evidence/external/R4-401/vultr-public-catalog-2026-08-25.json`.
