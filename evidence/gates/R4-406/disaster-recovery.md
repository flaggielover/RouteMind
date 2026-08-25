# R4-406 Disaster Recovery Evidence

Date: 2026-08-25 (Asia/Shanghai)

Entry revision: `fdc45cb3db879e0aadefce00bba22714a7d66c9b`

Status: `IMPLEMENTED / SERVICE_DRILL_PENDING / TARGET_PENDING`

## Recovery boundary

`scripts/disaster_recovery_drill.py` creates random ephemeral PostgreSQL,
RabbitMQ, and Redis source containers with generated credentials. It applies all
17 Java-owned migrations, creates two tenant fixtures, packages three
checksum-bound artifacts, destroys the source containers, and restores into new
containers. Cleanup targets only its generated container names and anonymous
volumes. No repository Compose volume, Vultr resource, production credential,
or production data is used.

The drill verifies PostgreSQL tenant, order, immutable transition audit, Outbox,
Inbox, courier-location, and detect-only reconciliation state. It restores a
RabbitMQ vhost-scoped definition file that contains no credential material,
replays one message per durable Outbox row, restores Redis RDB state, deletes one
tenant projection, and rebuilds it from PostgreSQL. It then mutates the isolated
audit state and proves an acknowledged rollback restores the original digest.

## Fail-closed evidence contract

`scripts/disaster_recovery.py` requires exactly 11 recovery checks, all three
service artifacts with SHA-256 and nonzero size, two-tenant digest continuity,
an acknowledged rollback manifest, an isolated source-destruction boundary, and
a self-digesting report. Five mutation-test groups reject missing or failed
checks, incomplete artifacts, digest drift, unsafe scope, stale report digests,
unacknowledged rollback, production claims, the wrong target identity, and RPO
or RTO above the frozen limits.

A local report is classified only as
`LOCAL_DRILL_PASS_TARGET_PENDING`. Even if its fixture RPO or measured restore
time is below the target limits, `require_target=True` rejects it. Target
qualification requires provider `Vultr`, region `nrt`, a matching external
evidence digest, RPO at most 900 seconds, and RTO at most 7200 seconds.

## Validation state

- `python -m py_compile scripts/disaster_recovery.py scripts/disaster_recovery_drill.py scripts/disaster_recovery_test.py`: PASS.
- `python scripts/disaster_recovery_test.py`: PASS, 5 tests.
- `./scripts/full-gate.ps1`: PASS, including 110 Java tests, 920 Python tests
  at 95.11% coverage, 104 Web tests, production build, all control contracts,
  and Compose configuration.
- `./scripts/resilience.ps1`: PASS when run serially, 15 Java and 2 Python
  tests. An earlier concurrent invocation raced the full gate's Maven `clean`;
  the retained serial result confirms no product regression.
- R4-401 closure commit `fdc45cb` passed all five GitHub Actions jobs in run
  `32843874880`.
- Implementation `13d689b` run `32845758884` passed control, Java, Python, Web,
  and the focused resilience baseline, then failed before restore because the
  RabbitMQ readiness probe incorrectly depended on diagnostic text appearing on
  stdout. The diagnostic command's exit code is now authoritative and future
  timeouts retain the container log tail. No service-backed recovery pass is
  claimed from the failed run.
- The local Docker daemon was unresponsive before the implementation checkpoint.
  The remediation CI run and its retained recovery JSON artifact are pending.

## Evidence boundary

This checkpoint does not close R4-406. It does not claim a Vultr resource,
Tokyo restore, production deployment, production data, production RPO/RTO, or
regional recovery. Matching credentialed Vultr Tokyo evidence plus explicit
resource/spend authorization remain required. R3-325 was not rerun, tuned,
reinterpreted, or changed and remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.
