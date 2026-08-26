# R4-405/R4-406 Tokyo VM External Validation Preparation

## Classification

This is design and offline preparation only. It creates no Vultr resource,
incurs no charge, performs no live workload, and supplies no target evidence.
R4-405 and R4-406 remain `TARGET_PENDING`.

The VKE diagnostic line is frozen without reinterpretation:

```text
EXTERNAL_VKE_VALIDATION = INCONCLUSIVE
R4-405 / R4-406 = TARGET_PENDING
NO_TARGET_CLAIM
NO_ROOT_CAUSE_CLAIM
```

All v1/v2/v3 attempt, failure, cost, and teardown evidence remains preserved.
There is no v4 design or execution authorization.

## Contract audit

R4-405's five-boundary correlation, tenant-safe cardinality/cost, Collector outage,
backpressure, recovery, and durable-business-truth requirements are independent of
Kubernetes. R4-406's PostgreSQL RPO/RTO, Outbox/Inbox/RabbitMQ/Redis restoration,
tenant/audit continuity, reconciliation, and rollback requirements are also
platform-neutral.

The former external plan bound resource sampling to Kubernetes Metrics API,
isolation to NetworkPolicy, queue storage to PVC/CSI, and topology identity to the
VKE control plane. The VM contract substitutes real Docker/cgroup/disk metrics,
internal networks plus Vultr firewall, bounded local-disk queues, and credentialed
VM/VPC identity. It does not call those substitutions VKE evidence.

`DEFERRED_VKE` explicitly covers VKE API/TLS, NetworkPolicy, Kubernetes Metrics
API, PVC/CSI reclaim, pod/worker anti-affinity, managed control-plane HA, and
Kubernetes rollout/namespace isolation.

## Prepared topology

The exact future topology is one `vc2-8c-32gb` primary VM, one
`vc2-2c-4gb` recovery VM, one `10.77.0.0/24` VPC, one firewall group, one exact
operator TCP 22 `/32` rule, and one private VPC TCP 22 rule, all in Vultr `nrt`.
There is no VKE, block storage, load balancer, public application ingress, or
public OTLP.

The primary runs the real RouteMind Java/Python/PostgreSQL/RabbitMQ/Redis workload,
an mTLS gateway Collector, an mTLS backend-ingress Collector, and self-hosted
SigNoz Foundry Compose. The recovery VM independently pulls an encrypted package
over the VPC and validates restore, reconciliation, and rollback.

Java and Python write real application logs to a bounded shared volume. The
gateway reads it through service-labelled, read-only filelog receivers, avoiding
Docker-socket access and host log ports while preserving trace/request evidence.

Before target rendering, Foundry runs with `--no-ledger --no-updater`; SigNoz
analytics, stats reporting, and identity collection are disabled; and product
telemetry is blocked at egress. The executor must generate and verify
execution-scoped metastore and
ClickHouse credentials from ACL-restricted secret files, while direct backend
ports remain unpublished. Either control failing verification aborts the run.

## Cost and authority

Read-only authenticated catalog values are USD 0.219/hour plus USD 0.027/hour.
The six-hour catalog upper bound is USD 1.476; the requested incremental Human
Gate ceiling is USD 3. Previous conservative VKE/diagnostic cost remains USD 11,
giving a combined ceiling of USD 14.

The contract keeps resource creation, spend, and live mutation authorization
false. Execution requires a fresh exact digest at
`ROUTEMIND TOKYO VM EXTERNAL VALIDATION HUMAN GATE` after local and CI validation.
The prepared canonical SHA-256 is
`2c6bd381ea8bdbf6a2c91864ec4bbf7589d434b19f043375322138ad7bfc608a`.

## Scientific boundary

No Round 3 experiment was rerun. R3-325 remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

## Local evidence

- contract validation and 14 directed fail-closed mutations passed;
- actual-workload qualification UUID/correlation regression passed;
- Terraform 1.9.8 formatted and validated Vultr provider 2.32.0 offline;
- Compose config and pinned Foundry 0.2.17 render passed with product telemetry
  disabled and no public application/OTLP ports;
- Java 113/113, Python 925/925 at 95.09%, Web 104/104 plus production build,
  focused resilience 16 Java / 2 Python, security, graph, and control gates passed.

These are preparation evidence only and do not qualify the target.

Implementation `0a900ce` passed all five jobs in real GitHub Actions run
`32993990760`. The Linux control-plane job ran the new offline
Terraform/Compose/Foundry gate; no provider mutation or target workload occurred.
