# R4-405 Tokyo VM SSH-readiness diagnostic v1 execution

Date: 2026-08-27

Execution ID: `r4-vm-ssh-v1-20260827t072548z-b0006d8c04`

Contract canonical SHA-256:
`2ba069c9886c69f1b38a22740c6c2367bd21a2bd129e8ff6c8148f336a46fbb7`

Result: `DIAGNOSTIC_INCOMPLETE / SSH_BANNER_NOT_RECEIVED / UNKNOWN`

## Authorization and boundary

The approved contract was consumed once. Authenticated preflight proved Vultr
`nrt` is Tokyo, plan `vc2-1c-1gb` was available, OS ID 2284 was Ubuntu 24.04
LTS x64, the configured local/provider ED25519 public fingerprints matched,
the operator ingress was one IPv4 `/32`, and the one-hour catalog upper bound
was USD 0.01 against the USD 1 ceiling.

The saved Terraform plan contained exactly three creates and no change or
delete: one VM, one firewall group, and one TCP 22 operator `/32` rule. It
created no VPC, VKE cluster, storage, load balancer, public application endpoint,
RouteMind workload, SigNoz deployment, or OTLP endpoint. Authenticated readback
proved the exact region, plan, image, instance label, firewall attachment, and
single rule before diagnosis.

## Staged observation

The provider reported `active / ok / running` with a public IPv4 address on the
first readiness observation at `2026-08-27T07:27:38Z`. Six bounded operator
probes ran from `07:27:38Z` through `07:29:53Z` with backoff
`0, 5, 10, 15, 30, 60` seconds. Every probe recorded:

- `VM_CREATED = PASS`
- `PUBLIC_IP_ASSIGNED = PASS`
- `TCP22_REACHABLE = PASS`
- `SSH_BANNER_RECEIVED = FAIL`
- KEX, host-key verification, authentication, cloud-init, and bootstrap stages
  were not reached

No independent provider-console host-key artifact was automated or retained.
Strict host-key checking therefore stopped before authentication, and no guest
readiness artifact was claimable. The missing guest artifact is recorded
explicitly rather than inferred away. The run is consequently
`DIAGNOSTIC_INCOMPLETE`, not a readiness pass.

This third minimal-VM observation weakens package installation or package-manager
contention as a sole explanation because this cloud-init performed no package
update, upgrade, or installation. It does not distinguish stock-image sshd,
host readiness, provider firewall/platform behavior, or the operator/VPN/TUN
network path. Root cause remains `UNKNOWN`; there is no provider-fault claim.

## Cleanup, cost, and leakage

Exact Terraform teardown deleted the diagnostic VM, its rule, and firewall
group. Authenticated provider checks proved the VM and firewall identities return
404 and the execution-label resource count is zero. A second GET-only finalizer
reverified both 404 results and zero labels. Retained provider resources: zero.

Runtime was four minutes. The conservative catalog upper bound is USD 0.01;
this is not an invoice claim. Cumulative conservative RouteMind external cost is
USD 11.256. The final leakage scan found zero secret, raw tenant identifier, or
production-data findings.

The initial local evidence finalization encountered a PowerShell array-binding
error only after teardown had completed and the exact cleanup artifact existed.
Commit `5b5d42b` fixed that local finalizer, passed all five jobs in real GitHub
Actions run `33050160883`, and completed GET-only cleanup re-verification,
leakage scan, and the manifest without recreating or mutating any resource.

Sanitized artifacts are retained outside Git under
`ROUTEMIND_DATA_ROOT/external-validation/r4-vm-ssh-v1-20260827t072548z-b0006d8c04/sanitized-evidence`.
The manifest contains 11 entries and has SHA-256
`aa4dabc54cfae06f93747477aef0af113cb2324a6e80ccca446c61f547e0e078`.

## Gate disposition

This diagnostic did not deploy RouteMind, SigNoz, OTLP, PostgreSQL, RabbitMQ,
or Redis. It cannot qualify tenant-safe telemetry, target failure/recovery, or
cross-VM DR. Therefore:

- R4-405 remains `LOCAL_AND_CI_VALIDATED / TARGET_PENDING / NO_TARGET_CLAIM`.
- R4-406 remains `LOCAL_CI_DRILL_VALIDATED / TARGET_PENDING / NO_TARGET_CLAIM`.
- `EXTERNAL_VKE_VALIDATION` remains frozen `INCONCLUSIVE`.
- `NO_ROOT_CAUSE_CLAIM` remains mandatory.
- R3-325 remains `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM` and was not rerun.

The contract digest is consumed and cannot authorize another execution.
