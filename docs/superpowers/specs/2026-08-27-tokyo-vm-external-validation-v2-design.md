# RouteMind Tokyo VM External Validation v2 Design

## Decision

Prepare a new no-new-VPC contract for R4-405/R4-406. The consumed v1 digest
remains immutable and cannot authorize v2. The five existing `nrt` VPCs are not
modified, deleted, attached, detached, or reused.

The selected topology retains one `vc2-8c-32gb` primary and one
`vc2-2c-4gb` recovery VM in `nrt`, one firewall group, and two exact TCP 22
rules. The operator rule admits only `ROUTEMIND_OPERATOR_CIDR` as an IPv4 `/32`.
The second rule is created only after the recovery VM receives its provider
identity and admits that exact public IPv4 `/32` for an encrypted recovery-package
pull from the primary. `VPC_CREATE_COUNT=0` and `VPC_REUSE_COUNT=0`.

## Alternatives

### Reuse an existing VPC

Rejected. Read-only provider inventory found five VKE-labelled VPCs and no
current instances, Kubernetes clusters, load balancers, bare metal, or managed
databases. Absence from those lists does not prove ownership, attachment
completeness, lifecycle compatibility, or deletion safety. Every existing VPC is
therefore `NOT_SAFE_TO_REUSE`.

### No-new-VPC topology

Selected. All workload, database, broker, cache, OTLP, Collector, ClickHouse,
SigNoz, and RouteMind internal traffic remains on un-published Docker networks on
the primary. Only the encrypted, digest-bound recovery package crosses hosts over
SSH, with public-key authentication, strict host-key checking, and a source `/32`
derived from the recovery provider identity. Raw payloads do not transit the
operator machine.

### Quota increase or VPC cleanup

Retained as a separate Human Gate option, but unnecessary for the selected
topology. RouteMind automation must never infer that an apparently unused VPC is
safe to delete or detach.

## Property Audit

R4-405 requires real workload telemetry, traces, metrics, logs, tenant-safe
cardinality/cost attribution, bounded failure injection, export recovery, and
durable business truth. R4-406 requires PostgreSQL RPO/RTO, Outbox/Inbox and
RabbitMQ reconciliation, Redis rebuildability, tenant/audit continuity, rollback,
and an independent recovery VM. Those are required properties.

A newly created VPC is an implementation choice. It is not needed when no service
port is exposed publicly and the only cross-VM data path is authenticated and
encrypted. VKE API/TLS, NetworkPolicy, Metrics API, PVC/CSI reclaim, pod
anti-affinity, managed control-plane HA, and Kubernetes rollout/namespace
isolation remain `DEFERRED_VKE` and cannot be promoted by VM evidence.

## Execution and Error Boundaries

The default action is offline validation. A future execution requires a new Human
Gate bound to the v2 canonical digest, an authenticated quote at or below USD 3,
an exact saved Terraform plan accepted by `r4_vm_external_plan_v2.py`, and a
six-hour timeout. The plan must contain exactly two instances, one firewall group,
two firewall rules, and zero VPC resources. `apply` may consume only that validated
saved plan.

The recovery-to-primary rule is deliberately provider-computed. It cannot exist
until the recovery VM identity exists, and it must resolve to one IPv4 `/32` before
the recovery package transfer. Failure to establish the rule, pin the SSH host key,
encrypt and digest-bind the package, or prove zero public service ports stops the
run.

## Teardown and Evidence

The execution owns exactly two VMs, one firewall group, and two rules. Teardown
removes Compose projects, volumes, generated secrets, the encrypted package, and
those exact provider identities, then requires exact 404 and zero execution-label
checks. It never owns or deletes a VPC.

Local gates and CI are preparation evidence only. Real R4-405/R4-406 target status
requires the full workload, telemetry, failure, recovery, leakage, cost, and
cleanup artifacts. R3-325 remains
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.
