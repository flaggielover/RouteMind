# Tokyo VPC Quota Resolution and VM v2 Preparation

## Classification

This is read-only provider audit and local preparation evidence. No Vultr resource
was created, modified, detached, attached, or deleted. It is not R4-405/R4-406
target evidence.

```text
provider = Vultr
region = nrt
observed_at = 2026-08-27T04:17:30Z
provider_mutation = NONE
v1_digest = 2c6bd381ea8bdbf6a2c91864ec4bbf7589d434b19f043375322138ad7bfc608a
v1_digest_consumed = true
```

## Read-only VPC audit

Authenticated GET-only inventory returned five VPCs in `nrt`:

| VPC identity | Created UTC | CIDR | Description | Related-resource result | Disposition |
| --- | --- | --- | --- | --- | --- |
| `389b488d-4e93-4fc5-81a6-41201a97b6a6` | `2026-08-26T00:28:14Z` | `10.25.96.0/20` | `VKE-Network-7e20a1bd-9462-4a45-8bfc-7bca12cebec0` | no listed related resources; completeness not proven | `UNKNOWN / NOT_SAFE_TO_REUSE` |
| `c932af08-dc45-40bf-b27c-598b59ec173e` | `2026-08-26T02:33:24Z` | `10.25.112.0/20` | `VKE-Network-4181e71c-82c4-431e-ae99-9070179e0bce` | no listed related resources; historical VKE identity matches repository evidence | `UNKNOWN / NOT_SAFE_TO_REUSE` |
| `70a08d2d-2666-4f02-ab89-28abe1e54e37` | `2026-08-26T05:13:43Z` | `10.25.128.0/20` | `VKE-Network-ce674059-284b-4ac2-a55e-09046f02e501` | no listed related resources; historical VKE identity matches repository evidence | `UNKNOWN / NOT_SAFE_TO_REUSE` |
| `5819ba36-748f-4a51-a2b6-70b075d00e0f` | `2026-08-26T09:47:39Z` | `10.25.144.0/20` | `VKE-Network-42c00adb-f85f-4c86-9b89-be7bf0ae00c9` | no listed related resources; historical VKE identity matches repository evidence | `UNKNOWN / NOT_SAFE_TO_REUSE` |
| `a19dd444-ad98-46e7-9ba1-b40f8aa57e09` | `2026-08-26T10:57:38Z` | `10.25.160.0/20` | `VKE-Network-7e60e031-9f28-4264-b055-371f599d0206` | no listed related resources; historical VKE identity matches repository evidence | `UNKNOWN / NOT_SAFE_TO_REUSE` |

The same read returned account and `nrt` counts of zero for instances, Kubernetes
clusters, load balancers, bare-metal servers, and managed databases. That does not
prove that a VPC is unused, unowned, lifecycle-compatible, or safe to delete.
Provider-only ownership remains `UNKNOWN`; repository identity correlation does
not grant lifecycle authority. Existing VPC reuse is therefore rejected.

## Required properties versus implementation choices

The real RouteMind workload, PostgreSQL durable truth, RabbitMQ messaging, Redis
rebuildability, Java/Python communication, OTLP signals, telemetry backend,
failure recovery, independent cross-VM restore, security, Tokyo residency, and
network isolation remain required properties. Creating a new VPC is an
implementation choice.

No-VPC does not make any service public. RouteMind, PostgreSQL, RabbitMQ, Redis,
OTLP, Collector health, ClickHouse, and SigNoz backend keep zero host-published
ports. The only cross-VM path is a recovery provider IPv4 `/32` TCP 22 rule for a
direct encrypted, digest-bound package pull with strict host-key verification.

## Prepared v2 contract

`r4-vultr-tokyo-vm-external-validation-v2` defines:

- one `vc2-8c-32gb` primary and one `vc2-2c-4gb` recovery VM in `nrt`;
- one firewall group and exactly two TCP 22 IPv4 `/32` rules;
- `VPC_CREATE_COUNT=0` and `VPC_REUSE_COUNT=0`;
- the unchanged real RouteMind, mTLS Collector, SigNoz, failure, recovery,
  leakage, residency, retention, cost, and cleanup evidence requirements;
- teardown ownership limited to two VMs, one firewall group, and two rules.

The canonical v2 SHA-256 is
`b1cf89b905b6bb42a98eba17de31fb21883ed94139301986a06247acc660a05b`.
The byte SHA-256 is
`a572e7fa0bd1eaa7a4ddeb8a60d3a9fcb5ba7cdd74ea411069e04591ec20ea65`.

## Local gates

- contract validation and 16 directed fail-closed tests passed;
- exact plan validator and seven mutation tests passed;
- GET-only audit static tests passed and the authenticated audit completed;
- Terraform 1.9.8/provider 2.32.0 `fmt/init/validate` passed;
- a real `-refresh=false` plan produced exactly five creates, zero changes, zero
  deletes, and zero VPC resources; it was not applied and its isolated plan
  directory was deleted;
- shared RouteMind Compose and pinned SigNoz Foundry gates passed;
- no secret value was retained in this evidence.

R4-405/R4-406 remain `TARGET_PENDING`; VKE remains
`EXTERNAL_VKE_VALIDATION = INCONCLUSIVE`, with `NO_TARGET_CLAIM` and
`NO_ROOT_CAUSE_CLAIM`. R3-325 remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

## Repository closure

Preparation commit `760e1ca` was pushed to `main`. Real GitHub Actions run
`33039469513` passed all five required jobs, including the Linux no-new-VPC v2
Terraform/Compose/Foundry gate. This proves repository preparation only and does
not authorize provider mutation or qualify R4-405/R4-406 target evidence.
