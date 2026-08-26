# R4 Vultr Tokyo VM External Validation

## Authority and current status

This runbook prepares a platform-neutral R4-405/R4-406 qualification. It does not
authorize provider mutation. The only current permitted command is the offline
gate:

```powershell
pwsh ./scripts/r4_vm_external_iac_gate.ps1
```

The VKE diagnostic lane is frozen as:

```text
EXTERNAL_VKE_VALIDATION = INCONCLUSIVE
R4-405 / R4-406 = TARGET_PENDING
NO_TARGET_CLAIM
NO_ROOT_CAUSE_CLAIM
```

All v1/v2/v3 attempt, failure, cost, and teardown evidence is immutable. There is
no automatic or prepared v4.

## Exact future resource inventory

- one `vc2-8c-32gb` primary VM in `nrt`;
- one `vc2-2c-4gb` recovery VM in `nrt`;
- one `10.77.0.0/24` Vultr VPC;
- one firewall group;
- one TCP 22 rule for the exact operator IPv4 `/32`;
- one private TCP 22 rule for `10.77.0.0/24`;
- zero VKE clusters, block-storage volumes, load balancers, snapshots, automatic
  backups, DDoS add-ons, and public application or OTLP endpoints.

The Terraform plan must contain exactly one `vultr_firewall_group`, two
`vultr_firewall_rule`, two `vultr_instance`, and one `vultr_vpc` create action.
Any other resource or action fails closed.

## Telemetry and workload topology

The primary VM builds the exact approved RouteMind source revision and runs real
Java, Python, PostgreSQL, RabbitMQ, Redis, and Outbox components. The qualification
performs a durable order, Twin simulation control, RouteBench experiment, and
asynchronous Outbox publication.

The telemetry path is:

```text
RouteMind workload
  -> RouteMind gateway Collector (mTLS, tenant deletion, persistent queue)
  -> backend ingress Collector (mTLS)
  -> SigNoz ingester (isolated signoz-network)
  -> Tokyo ClickHouse
```

SigNoz is rendered by official Foundry Compose. The Foundry Linux AMD64 archive
is pinned to `v0.2.17` and SHA-256
`51f41204b8048cd1f7e278fb5d2ba5d82d2ee8fb619bfe9330e2f8ceffc0d886`.
SigNoz is pinned to `v0.139.0`; Collector Contrib is `0.159.0`. Mutable image
tags are rejected before deployment and final OCI digests enter the environment
manifest.

Before target `forge`, the executor invokes Foundry with `--no-ledger
--no-updater`, renders SigNoz with analytics, stats reporting, and identity
collection disabled, and proves that product telemetry is blocked at egress. It
must also generate execution-scoped metastore
and ClickHouse credentials, inject them from ACL-restricted files, and verify
authentication. Inability to prove either control aborts before deployment; a
default anonymous backend configuration is not acceptable target evidence.

RouteMind, dependencies, collectors, ClickHouse, and OTLP expose no host ports.
The SigNoz UI binds `127.0.0.1:8080` and requires an operator SSH tunnel.
Java and Python application logs use a bounded shared volume mounted read-only by
two service-labelled filelog receivers; no Docker socket or host log port is
exposed.

## Secrets and data residency

The only user-configured secrets are `VULTR_API_KEY` and
`ROUTEMIND_SSH_PRIVATE_KEY_PATH`. The SSH private key remains outside Git.
`ROUTEMIND_VULTR_SSH_KEY_ID` and `ROUTEMIND_OPERATOR_CIDR` are non-secret
configuration. A future approval digest must be supplied as
`ROUTEMIND_VM_EXTERNAL_EXECUTION_APPROVAL_DIGEST`.

PostgreSQL, RabbitMQ, Redis, attribution, mTLS, SigNoz, and encrypted-package keys
are generated into an ACL-restricted execution directory outside the repository.
They are mounted as files and never written to Git, logs, evidence, fixtures,
screenshots, command arguments, or the Progress Capsule.

Only synthetic qualification data is permitted. Raw telemetry, Docker volumes,
and the encrypted recovery package remain in Vultr `nrt` and are deleted before
VM teardown. Sanitized evidence may leave Tokyo only after a zero-finding leakage
scan. Raw retention is at most six hours; sanitized evidence retention is at most
30 days.

## Failure and recovery sequence

1. Record credentialed VM, VPC, firewall, region, image, and source identities.
2. Prove both Collector health endpoints and both mTLS hops.
3. Run the actual RouteMind workload and query backend trace, metric, and log
   records.
4. Prove HTTP, messaging, worker, simulation, and experiment correlation without
   falsely forcing asynchronous work into one synchronous span tree.
5. Stop the gateway Collector, run workload, verify durable truth, restart, and
   prove queued export recovery.
6. Disconnect backend ingress from `signoz-network`, then reconnect and prove
   bounded recovery.
7. Stop the SigNoz ingester, run bounded telemetry, restart, and prove backend
   recovery.
8. Snapshot actual synthetic PostgreSQL state, RabbitMQ definitions, and Redis
   projection; bind digests and encrypt the package.
9. Have the recovery VM pull the package over the VPC and restore it into isolated
   containers.
10. Verify RPO/RTO, Outbox, Inbox, RabbitMQ topology/replay, Redis rebuild, tenant
    isolation, audit continuity, deliberate mutation, and rollback.
11. Record `docker stats`, cgroup, disk, queue, backend, and provider cost evidence.
12. Persist raw artifacts before aggregation and run the leakage scan.

Every failure phase has a bounded timeout and `finally` recovery. Telemetry
failure may not mutate or delete PostgreSQL durable truth.

## Evidence contract

Required sanitized artifacts are the authenticated resource manifest,
environment/version manifest, firewall readback, Collector health, actual
workload result, trace/metric/log queries, tenant/cardinality report,
failure/recovery timeline, target recovery report, resource use, cost bound,
leakage scan, cleanup inventory, and artifact manifest. Every artifact requires
UTC timestamps, byte length, and SHA-256.

Local Compose, mock output, provider documentation, screenshots, and green CI do
not count as target evidence. A VM result cannot claim VKE or production
deployment. VKE API/TLS, NetworkPolicy, Kubernetes Metrics API, PVC/CSI reclaim,
pod anti-affinity, managed control-plane HA, and Kubernetes rollout/namespace
isolation remain `DEFERRED_VKE`.

## Cost and teardown

The authenticated read-only catalog observation is USD 0.219/hour for
`vc2-8c-32gb` plus USD 0.027/hour for `vc2-2c-4gb`: USD 1.476 for six hours.
The future incremental approval ceiling is USD 3. Previous conservative VKE and
diagnostic cost is USD 11, so the combined conservative ceiling is USD 14.
Provisioning must abort if the authenticated quote exceeds USD 3.

Teardown stops both Compose projects, deletes every named volume, generated key,
encrypted package, plan, state, and known-host file, then destroys exactly the two
VMs, VPC, firewall group, and rules. It must verify exact provider identities are
404 and the execution-label count is zero. Broad region/account/project deletion
is forbidden.

## Human Gate

After local and CI gates pass, execution requires approval of the exact canonical
contract SHA-256 printed by `scripts/r4_vm_external_validation.py`. Approval of an
earlier VKE or diagnostic digest is invalid. R3-325 remains permanently frozen as
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

Prepared canonical SHA-256:
`2c6bd381ea8bdbf6a2c91864ec4bbf7589d434b19f043375322138ad7bfc608a`.
