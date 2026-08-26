# ADR 0036: Platform-neutral Tokyo VM external validation

## Status

Accepted for preparation; external execution requires a fresh Human Gate.

## Context

Three bounded VKE connectivity diagnostics did not produce a complete two-point
result. Their immutable outcome is `EXTERNAL_VKE_VALIDATION = INCONCLUSIVE`, with
`NO_TARGET_CLAIM` and `NO_ROOT_CAUSE_CLAIM`. Continuing to optimize VKE control
plane connectivity would not directly test R4-405 telemetry or R4-406 recovery.

The task-level acceptance contracts are platform-neutral. Their prior Kubernetes
binding came from the selected implementation topology, not from the reliability,
security, tenancy, residency, telemetry, or DR properties themselves.

## Decision

Use a bounded, isolated two-VM Vultr `nrt` qualification topology:

- `vc2-8c-32gb`: actual RouteMind workload, mTLS Collectors, and SigNoz Foundry
  Compose;
- `vc2-2c-4gb`: independent recovery, reconciliation, rollback, and cleanup
  observation;
- one `10.77.0.0/24` VPC, one firewall group, one operator SSH `/32` rule, and one
  private VPC SSH rule;
- no VKE, block storage, load balancer, public application ingress, or public OTLP.

SigNoz remains self-hosted in Tokyo. Foundry `v0.2.17`, SigNoz `v0.139.0`, and
OpenTelemetry Collector Contrib `0.159.0` are pinned; runtime image digests must be
resolved before deployment. Foundry's ledger and updater plus SigNoz analytics,
stats reporting, and identity collection are disabled, and product telemetry is
blocked at egress before target rendering. Execution-scoped metastore and ClickHouse
credentials are mandatory; failure to verify either control aborts the run.

## Consequences

The topology can produce real target evidence for the original R4-405/R4-406
properties at lower cost and with fewer failure surfaces. It does not validate
VKE or the R4-401 production topology. VKE API/TLS, NetworkPolicy, Kubernetes
Metrics API, PVC/CSI reclaim, pod anti-affinity, managed control-plane HA, and
Kubernetes rollout/namespace behavior remain `DEFERRED_VKE`.

The maximum future runtime is six hours. The catalog estimate is USD 1.476 and the
incremental fail-closed authorization ceiling is USD 3. No spend or resource
creation is authorized by this ADR.
