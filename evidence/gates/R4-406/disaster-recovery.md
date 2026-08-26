# R4-406 Disaster Recovery Evidence

Date: 2026-08-25 (Asia/Shanghai)

Entry revision: `cf6a63e039091c926b1dc7b2244557a8ebef3089`

Status: `LOCAL_CI_DRILL_VALIDATED / TARGET_PENDING`

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
- Readiness remediation `c109a27` run `32846265052` passed the same four jobs
  and resilience baseline and retained the actual RabbitMQ startup error:
  `.erlang.cookie: eacces` on the runner-provided anonymous data volume. The
  isolated drill now supplies a random in-memory Erlang cookie and mounts its
  Mnesia base on an explicit container tmpfs. Neither value is persisted in the
  report. No service-backed recovery pass is claimed from this failed run.
- Runtime-state remediation `55031d2` run `32846798159` passed the four other
  jobs, resilience, Rabbit startup, package creation, source destruction, main
  restore, replay, rebuild, and reached the rollback restore. PostgreSQL
  `pg_isready` accepted the temporary initialization server before database
  `routemind` existed, so the final `pg_restore` raced database creation. The
  readiness condition now executes `SELECT 1` against the target database. No
  service-backed recovery pass is claimed from this failed run.
- Readiness remediation `cf6a63e` passed all five jobs in GitHub Actions run
  `32847143691`. The recovery step and artifact upload both passed.
- Retained artifact `9562802809`, named
  `r4-406-local-recovery-cf6a63e039091c926b1dc7b2244557a8ebef3089`, has
  GitHub artifact digest
  `sha256:c89ea3a51f14f72cb92598c3c26c1e01681cd517567fe4b0919bf02189f112a4`.
  Its downloaded report byte SHA-256 is
  `4493027b8b4d47200940152af4eee6874acb332386d9b3cbe3c141d76ef071db`
  and its self-digest is
  `8977fb21a8c47fea51cab0b4f7b9b4f92f7d2de935cc1b8ca09e42e86bb880f3`.
- Independent validation returned `LOCAL_DRILL_PASS_TARGET_PENDING` and
  `TARGET_NOT_QUALIFIED`. All 11 checks passed for two tenants; package digest
  `fb0845e75c2a22daf534ce4467eb5e671386ac11109011fbc4df91d349c68c51`
  binds the PostgreSQL, RabbitMQ, and Redis artifacts. Source, restored, and
  rollback continuity digests all equal
  `315eaf1bbaeb74ff271c7b669ebf6d6d53b4f9d1744f4310ce0a458e561f07a8`.
- The CI fixture measured zero-second fixture RPO, 11.826-second restore, and
  3.31-second rollback. These are isolated runner observations only and are not
  Vultr Tokyo or production RPO/RTO evidence.
- The local Docker daemon was unresponsive before the implementation checkpoint;
  the real GitHub-hosted service drill now supplies the retained local-CI result.

## Evidence boundary

This evidence does not close R4-406. The task is externally blocked after its
local/CI lane. It does not claim a Vultr resource,
Tokyo restore, production deployment, production data, production RPO/RTO, or
regional recovery. Matching credentialed Vultr Tokyo evidence plus explicit
resource/spend authorization remain required. R3-325 was not rerun, tuned,
reinterpreted, or changed and remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

## Vultr Tokyo execution preparation

The shared R4-405/R4-406 external contract now freezes a temporary
`vhp-2c-4gb-amd` recovery host in `nrt`, public SSH limited to the operator's
single IPv4 `/32`, an existing public SSH key identity, automatic backups off,
synthetic fixtures only, and exact cleanup. Target mode additionally requires a
credentialed Vultr resource ID, UTC observation time, resource-manifest digest,
and `SYNTHETIC_NO_CUSTOMER_DATA`; local reports cannot be promoted.

The controller transfers only a non-secret target identity, checks out the
exact Git revision on the isolated host, runs the existing source-destroy/
restore/reconcile/rollback drill, downloads the sanitized report, and validates
it with `require_target=True`. SSH host state and restricted execution material
are removed during teardown. This is preparation only: no remote host exists,
no target drill ran, and R4-406 remains
`LOCAL_CI_DRILL_VALIDATED / TARGET_PENDING`.

## First Vultr attempt

Execution `r4-ext-20260826t042548z-eb70db776c` created the approved temporary
Tokyo VKE, recovery instance, firewall group, and SSH rule, but failed before
the controller invoked the recovery drill. No recovery fixture or production
data reached the host. Exact Terraform teardown and credentialed zero-inventory
checks passed; the conservative one-hour attempt cost bound is USD 0.24.
This is cleanup evidence, not target recovery evidence, so R4-406 remains
`LOCAL_CI_DRILL_VALIDATED / TARGET_PENDING`. The shared attempt record is
`evidence/gates/R4-405/2026-08-26-external-attempt-1.md`.

The corrected shared contract has SHA-256
`4956d29a5cbd69344a70c4d89514608b1acd32924e0598155c7f90848be77393`.
At that stage, another external attempt required approval of that exact digest;
the existing local-CI recovery result could not substitute for it.

## Second Vultr attempt

Execution `r4-ext-20260826t054111z-ea80181368` stopped at the VKE control-plane
firewall before any recovery fixture was transferred or drill command ran. The
active recovery instance contained only its synthetic cloud-init identity.
Exact teardown and zero-inventory checks passed; the second-attempt conservative
cost bound is USD 0.24 and the two-attempt aggregate bound is USD 0.48. This is
cleanup evidence, not target recovery evidence. Shared details are in
`evidence/gates/R4-405/2026-08-26-external-attempt-2.md`.

The shared contract now includes the missing operator `/32` VKE API rule and has
SHA-256
`c2a1695104ba7297b51b1c949fa689a4efeb5974dcf1a2122c12f91a57f4e2df`.
At that stage, R4-406 remained `LOCAL_CI_DRILL_VALIDATED / TARGET_PENDING` until
that exact contract was approved and the credentialed target drill completed.
The shared VKE firewall remediation revision `160f670` passed all five jobs in
real GitHub Actions run `32937109761`, including the independent local-CI
recovery drill. That result remains non-target evidence.

## Third Vultr attempt

Execution `r4-ext-20260826t063255z-18f9f4f51b` applied the approved five-resource
Tokyo plan under digest `c2a1695104ba7297b51b1c949fa689a4efeb5974dcf1a2122c12f91a57f4e2df`.
The VKE API still closed TLS before handshake despite the operator-only `/32`
firewall rule, so no recovery fixture or DR command ran. Kubernetes mutation did
not start. Teardown destroyed all five resources and credentialed zero-inventory
checks passed. The attempt's quote bound is USD 3.92 and the three-attempt
aggregate conservative bound is USD 4.40. R4-406 remains
`LOCAL_CI_DRILL_VALIDATED / TARGET_PENDING`; this is cleanup evidence, not
Tokyo recovery evidence.
Evidence checkpoint `fd94ce2` passed all five jobs in real GitHub Actions run
`32945284919`, including the independent recovery job. This remains non-target
evidence.

The subsequent read-only VKE connectivity audit is recorded in
`docs/closure/r4/VKE_TLS_EOF_DIAGNOSTIC.md`. It keeps target DR evidence
pending and proposes a two-observer, no-PVC diagnostic only; the prepared
contract digest `30c9580e...4a426` is not an approval or a recovery result.
The preparation commit `98b2877` passed all five jobs in Actions run
`32948600781`; this does not qualify Tokyo recovery evidence.

## VKE connectivity diagnostic attempt

Execution `r4-diag-20260826t091304z-ec5bcf4d62` did not deploy or execute a DR
fixture. Its operator probe observed TCP success and TLS EOF, but no Tokyo
observer artifact was retained, so the connectivity result is
`DIAGNOSTIC_INCOMPLETE / INSUFFICIENT_EVIDENCE`. Exact cleanup later proved all
four provider identities absent and zero execution-label resources. This is
cleanup evidence only, not Tokyo restore/reconciliation/RPO/RTO evidence.
R4-406 remains `LOCAL_CI_DRILL_VALIDATED / TARGET_PENDING`; the consumed
`30c9580e...4a426` digest is not reusable and any retry requires the new v2
contract Human Gate.

## VKE connectivity diagnostic attempt 2 (v2)

Execution `r4-diag-20260826t134703z-03f22ab836` used approved digest
`1f78b9d3562a6bac3cfa7b9ad070545e5b1eb2c7c9d88090acc9e765c20dc782` and
created only the bounded six-resource diagnostic shape. The Operator probe
recorded `DNS_OK / TCP_OK / TLS_EOF`; a PowerShell JSON case-collision in the
proxy status object stopped the controller before the Tokyo observer probe.
No recovery fixture, PostgreSQL restore, reconciliation, PVC, or Kubernetes
workload ran. The result is `DIAGNOSTIC_INCOMPLETE / INSUFFICIENT_EVIDENCE` and
does not qualify R4-406.

Exact teardown and credentialed cleanup checks completed (four provider `404`
responses, zero execution-label matches); no resource was retained. The
attempt quote bound is USD 2.20 and the conservative aggregate is USD 8.80.
The parser defect is fixed locally with a regression test, but any future
two-observer retry requires a new contract digest and Human Gate. R4-406
remains `LOCAL_CI_DRILL_VALIDATED / TARGET_PENDING`.

## v3 preparation (not target recovery evidence)

The independent-artifact v3 connectivity contract is prepared at
`contracts/external-validation/r4-vultr-tokyo-vke-connectivity-diagnostic-v3.json`
with SHA-256
`e1489efe5a21a464389322e29e85da992fee7c0038e4817f4e8392693d16d660`.
Preparation performs no Vultr writes and creates no recovery fixture, storage,
or Kubernetes workload. It only defines a bounded two-observer diagnostic:
each side persists raw output before parsing and records canonical DNS, IP, TCP,
TLS ClientHello, TLS handshake, and HTTP phases independently. Execution,
malformed, missing, and aggregation failures are fail-closed and preserve the
other side's artifact; local tests exercise all six single-point failures.

The exact one-worker Tokyo VKE, recovery observer, firewall, operator SSH
`/32`, and two VKE API TCP 6443 `/32` rules remain the only permitted resources.
Maximum runtime is two hours, incremental cost is capped at USD 5.00, and
teardown requires identity-scoped destroy plus four `404` checks and zero
execution-label resources. R4-406 remains
`LOCAL_CI_DRILL_VALIDATED / TARGET_PENDING`; v3 preparation is not restore,
reconciliation, RPO/RTO, or target DR evidence. Approval must be given at
`VKE CONNECTIVITY DIAGNOSTIC V3 HUMAN GATE` for the exact digest above.
