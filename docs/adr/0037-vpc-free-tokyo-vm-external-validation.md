# ADR 0037: VPC-free Tokyo VM external validation

## Status

Accepted for preparation; external execution requires the v2 Human Gate.

## Context

The approved v1 Tokyo VM attempt stopped before VM creation because the Vultr
account had reached the five-VPC-per-region quota in `nrt`. Its digest is consumed.
A read-only audit found five VKE-labelled VPCs and zero listed related instances,
Kubernetes clusters, load balancers, bare-metal servers, or managed databases.
That observation does not prove ownership, complete non-use, lifecycle
compatibility, or safe reuse, so no existing VPC may be reused or deleted.

The R4-405/R4-406 acceptance properties require isolated workload and telemetry
traffic plus independent encrypted recovery. They do not require a newly created
provider VPC.

## Decision

Prepare `r4-vultr-tokyo-vm-external-validation-v2` with:

- one `vc2-8c-32gb` primary VM and one `vc2-2c-4gb` recovery VM in `nrt`;
- one execution-owned firewall group and two TCP 22 IPv4 `/32` rules;
- operator `/32` access to both hosts;
- recovery provider IPv4 `/32` access for a direct encrypted SSH package pull;
- zero created, attached, reused, detached, modified, or deleted VPCs;
- zero public RouteMind, PostgreSQL, RabbitMQ, Redis, OTLP, Collector, ClickHouse,
  or SigNoz backend ports; the SigNoz UI remains loopback-only through SSH.

The cross-VM package uses public-key SSH, strict host-key checking, a persisted
fingerprint, pre-transfer encryption, and SHA-256 binding. No raw package may
transit the operator machine.

## Consequences

The v2 topology preserves the platform-neutral telemetry and disaster-recovery
evidence contract without consuming VPC quota. Public exposure increases only by
one provider-derived recovery IPv4 `/32` rule on TCP 22; no service port is added.
The exact Terraform plan and destroy plan are executable gates.

VKE-specific properties remain `DEFERRED_VKE`. The v2 preparation is not target,
production, VKE, or scientific evidence. No paid resource or provider mutation is
authorized by this ADR.
