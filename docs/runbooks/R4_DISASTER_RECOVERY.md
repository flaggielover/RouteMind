# R4 Disaster Recovery Runbook

## Scope and authority

This runbook covers checksum-verified recovery packages for PostgreSQL,
RabbitMQ vhost topology, and Redis RDB state. PostgreSQL remains durable truth.
RabbitMQ can be repopulated from durable Outbox rows, and Redis GEO state can be
rebuilt from tenant-scoped PostgreSQL courier locations. Reconciliation remains
detect-only and cannot repair durable state.

The automated drill uses only random, ephemeral container names and generated
credentials. It destroys those source containers before restore and removes the
matching scratch containers and anonymous volumes afterward. It must never be
pointed at a production database, broker, cache, volume, or credential.

## Local and CI rehearsal

Run:

```powershell
python scripts/disaster_recovery_drill.py
```

The drill applies the repository migrations to PostgreSQL, creates two isolated
tenant fixtures, records lifecycle audit, Outbox, Inbox, courier, and detect-only
reconciliation state, and exports all three recovery artifacts. It then removes
the source containers before starting fresh restore containers.

The restored environment must prove:

1. PostgreSQL source and restore digests are identical across both tenants.
2. Order audit, Outbox IDs, Inbox IDs, and reconciliation evidence are retained.
3. RabbitMQ durable exchange, queue, and binding definitions are restored.
4. Restored Outbox rows can republish the expected number of RabbitMQ messages.
5. Redis RDB state restores, then a deleted tenant GEO projection is rebuilt
   only from PostgreSQL courier locations.
6. A deliberate isolated audit deletion changes the digest, and restoring the
   acknowledged package returns the original digest.

The generated report is written to
`evidence/tests/tmp/R4-406/local-drill.json`. CI retains it as
`r4-406-local-recovery-<git-sha>` for 30 days. The report validator rejects
missing checks, changed digests, incomplete artifacts, unacknowledged rollback,
production claims, and target claims made from local Docker evidence.

## Vultr Tokyo qualification

R4-401 fixes the target as Vultr `nrt` (Tokyo) with Japan/Tokyo data residency.
R4-406 cannot pass from local or CI Docker evidence. A target drill requires:

- explicit resource and spend authorization plus credentials supplied through
  an approved secret channel;
- isolated non-production recovery resources in `nrt` with verified storage
  residency;
- a target report that identifies provider `Vultr`, region `nrt`, and a SHA-256
  digest of matching remote evidence;
- measured PostgreSQL RPO at most 900 seconds and end-to-end RTO at most 7200
  seconds; and
- retained remote timestamps, resource identities, logs, checksums, cleanup,
  tenant/audit/replay/rebuild/reconciliation results, and cost evidence.

Meeting the numerical limits in local Docker does not qualify the target. The
validator returns `TARGET_NOT_QUALIFIED` until the matching target report exists.

## Target execution and rollback

Before a target drill, verify exact resource IDs, backup destination, encryption,
Tokyo residency, TTL, estimated cost, and deletion scope. Capture a new backup,
record its last committed durable timestamp, and freeze writes only within the
approved isolated drill scope. Restore PostgreSQL first, then RabbitMQ topology,
then Redis, replay durable Outbox work, rebuild projections, and run detect-only
reconciliation. Compare both tenants, audit chains, Inbox IDs, and Outbox IDs.

If any check fails, retain logs and checksums, stop traffic to the restore target,
and execute only the acknowledged rollback manifest. Never delete or overwrite
the source environment as part of target qualification. Cleanup resource IDs
must be reviewed against the approved drill inventory before deletion.
