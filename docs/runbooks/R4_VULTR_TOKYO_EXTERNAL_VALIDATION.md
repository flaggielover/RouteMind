# R4 Vultr Tokyo External Validation Runbook

## Status and authority

This runbook is prepared but not authorized for external execution. Its default
action is offline validation. `LivePreflight`, `Provision`, `Deploy`,
`Validate`, `Teardown`, and `Full` require all of:

- the explicit `-AcknowledgeExternalExecution` switch;
- `ROUTEMIND_EXTERNAL_EXECUTION_APPROVAL_DIGEST` equal to the frozen contract
  digest;
- the two required secrets and two non-secret target values listed below.

No current repository evidence proves a live Vultr resource, target telemetry,
target recovery, production deployment, or production readiness.

## Infrastructure and cost boundary

The exact Terraform create inventory is one recovery firewall group, two
allowlisted rules (recovery SSH and VKE API), one `vhp-2c-4gb-amd` recovery
instance, and one HA VKE with three
`vhp-4c-8gb-amd` workers in `nrt`. Kubernetes creates exactly five CSI block
volumes totaling 55 GiB, bounded by a 60 GiB quota. The VKE has no autoscaling. Automatic
backups, DDoS add-on, IPv6 on the recovery host, activation email, public load
balancers, public application ingress, and provider-managed cold storage are
disabled.

Authenticated catalog values are read before any create plan. The controller
aborts if the required plans are unavailable in `nrt`, if no exact VKE version
or Ubuntu 24.04 x64 image is available, or if the eight-hour upper bound exceeds
USD 15. Public-catalog expectation is at most USD 5. The independent R4-401
emergency monthly ceiling remains USD 300; this execution does not authorize it.

Official provider references:

- https://registry.terraform.io/providers/vultr/vultr/latest/docs
- https://docs.vultr.com/products/compute/kubernetes/provisioning
- https://docs.vultr.com/products/compute/kubernetes/management/destroy
- https://docs.vultr.com/how-to-provision-persistent-volume-claims-on-vultr-kubernetes-engine

## Topology, network, and TLS

The data path is the actual synthetic RouteMind workload (Java durable API,
Python compute API, and asynchronous Outbox relay) plus an OTLP connectivity
probe -> RouteMind Collector -> SigNoz Collector ->
Tokyo ClickHouse. RouteMind Collector has two replicas, 500 mCPU / 512 MiB
limits each, and a 10 GiB persistent queue per replica. The observability
namespace is limited to 8 CPU, 16 GiB memory, five PVCs, and 60 GiB storage.
The expected claims are 30 GiB ClickHouse, 3 GiB ZooKeeper, 2 GiB SigNoz
metadata, and two 10 GiB Collector queues: 55 GiB total. A LimitRange supplies
bounded defaults to chart helper containers that omit explicit limits.

Network surfaces are:

- TCP 4317 and 4318: OTLP gRPC/HTTP, `ClusterIP` only, mutual TLS;
- TCP 13133 and 8888: Collector health/diagnostics, `ClusterIP` only;
- TCP 8080: SigNoz UI, local `kubectl` control-plane tunnel only;
- TCP 22: recovery host, temporary public IPv4, exactly one operator `/32`;
- TCP 443: Vultr provider API, outbound only, TLS 1.2 or newer;
- TCP 6443: VKE Kubernetes API, temporary public control plane restricted to the
  operator `/32`, with kubeconfig CA and hostname validation retained even when
  a local fake-DNS resolver requires the provider-returned control-plane IP.

Default-deny NetworkPolicies protect the observability, application, and
validation namespaces. Application dependencies remain namespace-internal;
the application and labeled validation namespaces may enter RouteMind OTLP,
and only the observability namespace may scrape application metrics. Source and
package retrieval is limited to outbound TCP 443 during the bounded run. Failure injection removes
normal internal egress before applying a DNS-only Collector policy and always
restores the policy in `finally`.

An ephemeral private CA creates separate server and client identities after
provisioning. Certificate private keys, kubeconfig, ClickHouse password,
Terraform state, and plans live only in the ACL-restricted execution directory
under `ROUTEMIND_DATA_ROOT`; teardown deletes them. No public plaintext OTLP is
allowed.

## Secret injection

Required secrets:

- `VULTR_API_KEY`: process environment only, with the least Vultr scope needed
  for VKE, instance, firewall, and attached CSI volume lifecycle;
- `ROUTEMIND_SSH_PRIVATE_KEY_PATH`: absolute local path outside the repository.

Required non-secret configuration:

- `ROUTEMIND_VULTR_SSH_KEY_ID`: an existing Vultr public SSH key identity;
- `ROUTEMIND_OPERATOR_CIDR`: the operator's current public IPv4 `/32`.

Set secrets in the local process/OS secret facility or a protected GitHub
Environment only. Never place a value in chat, Git, tracked `.env`, evidence,
logs, fixtures, screenshots, or the Progress Capsule. The controller checks only
presence and never prints values. Generated mTLS keys, ClickHouse password, and
recovery fixture credentials are execution-scoped and destroyed. Backend queries
run in a short-lived Job whose password comes from a Kubernetes Secret; the
password is never placed in a local process argument or query output.

## Data and retention constraints

Only generated synthetic qualification data is allowed. Customer identity,
courier paths, merchant operations, tenant production events, notification
content, and production recovery data are forbidden. Raw telemetry and state
remain in Vultr `nrt` and are deleted before VKE teardown. Provider automatic
backups are off. Sanitized evidence may leave Tokyo after a leakage scan and is
retained for at most 30 days.

## Execution

Use PowerShell 7 (`pwsh`). The controller declares this runtime explicitly so
Windows PowerShell 5.1 cannot fail later on modern path and cryptography APIs.

Offline preparation is always safe:

```powershell
./scripts/r4_external_validation.ps1 -Action OfflinePreflight
```

After the final Human Gate and secure credential configuration, bind approval
to the exact digest and run one bounded execution:

```powershell
$env:ROUTEMIND_EXTERNAL_EXECUTION_APPROVAL_DIGEST = '<approved contract digest>'
./scripts/r4_external_validation.ps1 -Action Full -AcknowledgeExternalExecution
```

The generated execution ID binds source revision, target labels, state, quote,
evidence, and cleanup. Terraform plan validation rejects extra resource types or
non-create actions. Helm chart SHA and rendered image digests must resolve before
install. Re-running an individual phase uses the same `-ExecutionId`; broad or
label-only deletion is forbidden.

## Validation and Evidence Contract

All checks are fail-closed. A final pass requires:

1. credentialed Vultr resource identities and `nrt` region;
2. two healthy RouteMind Collector replicas;
3. successful mTLS OTLP connectivity;
4. backend evidence from the actual synthetic RouteMind workload: HTTP,
   messaging, worker, simulation, and experiment spans; the asynchronous
   worker is related by the event trace identity, not falsely forced into one
   synchronous span tree;
5. an actual ClickHouse metric sample for
   `routemind_telemetry_attributed_records_total`;
6. an actual correlated OTLP log carrying the recovered trace ID;
7. one bounded pseudonymous tenant key and no raw identity;
8. an actual scan of every sanitized evidence file with zero secret, raw tenant,
   or production marker findings;
9. network, RouteMind Collector, and SigNoz Collector outage behavior;
10. export recovery plus unchanged synthetic business outcomes;
11. the R4-406 target drill on the credentialed recovery host, with no
    production claim;
12. resource consumption from Kubernetes Metrics API and bound PVCs;
13. authenticated bounded cost evidence;
14. exact resource deletion and credentialed zero-inventory checks.

The 13 named artifacts have UTC timestamps, relative paths, byte sizes, and
SHA-256 digests. Probe output cannot substitute for a backend query. Local
Compose, mocks, provider documentation, screenshots, or a green CI run cannot
substitute for target evidence. The report assembler refuses any missing or
leaking artifact and will not emit `EXTERNAL_VALIDATION_PASS` until cleanup is
complete.

## Failure recovery and teardown

`Full` enters Terraform-backed teardown in `finally` after any provisioning
attempt with state. Helm and all three validation namespaces are deleted first so CSI volumes
can reclaim. The controller then waits for every captured volume identity to
return 404, validates an exact Terraform destroy plan, destroys VKE/instance/
firewall resources, and checks each exact API identity, both firewall groups,
and execution labels.

It then deletes kubeconfig, Terraform state/data/plans, SSH known-host state,
and generated secret material. Sanitized cleanup evidence records only resource
IDs, timestamps, and boolean results. If cleanup cannot prove an exact target,
returns a non-404 provider error, or leaves an ID, the run fails and retains the
restricted state and IDs for the same `Teardown -ExecutionId` recovery. It never
widens deletion by project, region, account, or unverified label.

R4-405/R4-406 status may change only after the final report validates, is
committed without secrets, passes GitHub Actions, and the graph is recomputed.
R3-325 must remain `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM` throughout.
