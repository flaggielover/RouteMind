# R4 Vultr Tokyo VM External Validation v2

## Authority

This runbook prepares the no-new-VPC alternative. It does not authorize
`terraform apply` or any Vultr mutation. The v1 digest is consumed and must not be
reused. The only provider operation authorized during preparation is the GET-only
audit:

```powershell
pwsh ./scripts/r4_vpc_quota_audit.ps1
```

Offline validation is:

```powershell
pwsh ./scripts/r4_vm_external_iac_gate_v2.ps1
```

## Exact topology

- one `vc2-8c-32gb` primary VM in `nrt`;
- one `vc2-2c-4gb` recovery VM in `nrt`;
- one firewall group;
- one operator IPv4 `/32` TCP 22 rule;
- one provider-computed recovery IPv4 `/32` TCP 22 rule;
- zero VPC creates, reuses, attachments, detachments, mutations, or deletes;
- zero VKE, block storage, load balancers, snapshots, or automatic backups.

The plan gate accepts exactly five create actions and rejects any update/delete,
extra resource, VPC, wide CIDR, extra port, wrong region, or expanded VM shape.
Future apply may use only the validated saved plan.

## Network and transfer

The RouteMind workload, PostgreSQL, RabbitMQ, Redis, both Collectors, OTLP,
ClickHouse, and SigNoz backend publish no host port. SigNoz UI binds
`127.0.0.1:8080` and is available only through an operator SSH tunnel.

After the recovery VM receives its main IPv4, Terraform adds that exact `/32` as
the second SSH source. The recovery VM pins the primary host-key fingerprint and
pulls a pre-encrypted, SHA-256-bound package directly. Password authentication,
plaintext cross-VM service traffic, operator relay, `0.0.0.0/0`, and `::/0` are
forbidden.

## Validation sequence

1. Re-run contract, environment, authenticated quote, and GET-only VPC audit.
2. Generate and validate the exact saved plan; verify five creates and zero VPC.
3. Obtain approval for the new canonical v2 digest.
4. Apply only the validated plan and read back region, VM, firewall, and rule
   identities.
5. Pin SSH host keys, verify key-only authentication, and bootstrap secrets in an
   ACL-restricted external execution directory.
6. Deploy the real RouteMind and pinned SigNoz runtime with no public service
   ports.
7. Collect traces, metrics, logs, tenant/cardinality/cost, failure/recovery, and
   durable-truth evidence.
8. Create, encrypt, and digest the recovery package; pull it directly from the
   recovery VM and validate restore, reconciliation, RPO/RTO, continuity, and
   rollback.
9. Run leakage and cost checks before sanitized evidence leaves Tokyo.
10. Delete runtime data and exact execution-owned provider resources, then verify
    404 identities and zero execution-label resources. Never delete a VPC.

## Human Gate

The final gate must name the exact canonical v2 SHA-256, both VM plans, region
`nrt`, six-hour maximum, USD 3 incremental ceiling, the two exact `/32` SSH rules,
zero VPC, and exact teardown. Approval of v1 or any VKE diagnostic digest is
invalid.
