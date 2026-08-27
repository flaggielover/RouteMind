# Tokyo VM SSH-Readiness Diagnostic v1 Preparation

## Classification

This is design and local-validation evidence only. No Vultr resource was
created, modified, or deleted, no Terraform plan was applied, and no spend was
authorized. R4-405 and R4-406 remain target-pending.

```text
contract = r4-vultr-tokyo-vm-ssh-readiness-diagnostic-v1
canonical_sha256 = 2ba069c9886c69f1b38a22740c6c2367bd21a2bd129e8ff6c8148f336a46fbb7
status = PREPARED_NOT_APPROVED_NOT_EXECUTED
region = nrt
root_cause = UNKNOWN
```

## Frozen predecessor facts

VM v2 execution `r4-vm-v2-20260827t051846z-7c7bd60337` remains immutable. Both
provider-active VMs accepted TCP 22 and then closed before an SSH server banner
or KEX could be retained. One bounded recovery reboot was unchanged. Exact
teardown left zero provider resources. Its conservative cost is USD 0.246 and
the cumulative conservative external cost remains USD 11.246.

TCP connection success proves only that the routed endpoint accepted a TCP
handshake. It does not prove that `sshd` produced an SSH identification string,
started KEX, presented the expected host identity, attempted public-key
authentication, authenticated the expected image user, completed cloud-init,
or reached bootstrap readiness. The historical root cause therefore remains
`UNKNOWN`.

The v2 cloud-init audit found package update/install and Docker startup work,
but no explicit `sshd` restart, network restart, reboot, `authorized_keys`
rewrite, or user creation. Package activity is a possible first-boot timing or
contention factor, not a proved root cause. The contract retains an A-P
candidate matrix covering daemon readiness/failure, cloud-init/package effects,
keys, username, host-key generation, rate limiting, firewall/host policy,
operator VPN/TUN path, image regression, and provider platform networking. Each
candidate records supporting evidence, contradiction, current confidence, and
one discriminating test.

## Minimal diagnostic boundary

- One `vc2-1c-1gb` VM in `nrt`, one firewall group, and one exact operator IPv4
  `/32` TCP 22 rule.
- Ubuntu 24.04 LTS x64, public catalog OS ID `2284`, Terraform
  `user_scheme = root`.
- Injected ED25519 public-key fingerprint
  `SHA256:JHiQkjaVyp5ft91S12iyyCbDB6PCAGhDqYTVnMJAUeI`. Future paid preflight must
  prove equality across the external private key's derived public fingerprint,
  the configured Vultr SSH key readback, and the guest authorized-key
  fingerprint. No private key is stored or printed.
- No VPC, second VM, VKE, block storage, load balancer, public HTTP endpoint,
  RouteMind, SigNoz, OTLP, database, messaging, cache, package install, reboot,
  or `sshd`/network restart.
- Maximum runtime 60 minutes. The current public catalog rate is USD 0.007/hour;
  the fail-closed incremental ceiling is USD 1 and requires an authenticated
  re-quote before any approved apply.

One VM is sufficient for the next information step because the immediate
question is the earliest failed image/boot/operator SSH stage, not workload or
cross-VM qualification. A second VM would add cost without improving that first
stage boundary. Any later topology expansion requires a new contract and gate.

## Stage and evidence design

The ordered success path is:

```text
VM_CREATED
PUBLIC_IP_ASSIGNED
TCP22_REACHABLE
SSH_BANNER_RECEIVED
SSH_KEX_STARTED
SSH_HOST_KEY_VERIFIED
SSH_AUTH_STARTED
SSH_AUTHENTICATED
CLOUD_INIT_COMPLETE
ROUTEMIND_BOOTSTRAP_READY
```

Polling is bounded into provider (10 minutes), TCP (10), banner/KEX (15),
strict host-key/auth (15), and cloud-init/bootstrap (10) phases. Backoff is
bounded at 60 seconds and no automatic reboot is allowed.

The operator probe uses `StrictHostKeyChecking=yes`; `accept-new` is forbidden.
Authentication cannot begin until the ED25519 key returned by `ssh-keyscan`
matches the independently retained guest/provider-console SHA-256 and its exact
host binding is atomically written to `known_hosts`. Host key absent, changed,
mismatch, authentication rejection, and username rejection remain distinct
terminal classes.

Cloud-init performs no package work and does not mutate `sshd`, networking, or
authorized keys. It atomically writes a local artifact containing cloud-init,
`ssh.service`, listener, `sshd -t`, public host-key fingerprints, public
authorized-key fingerprints, permissions, and expected-key match. The same
sanitized payload is emitted to the provider console with a SHA-256. If neither
strict SSH nor console retention can recover it, the diagnostic is incomplete;
the local file alone cannot be claimed as external evidence.

Operator and guest raw artifacts are persisted before aggregation. The harness
also supports independent multi-target artifacts so a malformed, missing, or
failed side cannot block or delete another side. Aggregation failure leaves raw
bytes unchanged.

## Local gates

- 21 artifact/protocol/state/fault tests cover TCP timeout/reset, TCP OK without banner,
  malformed banner, KEX timeout, host-key mismatch, auth rejection, wrong
  username, incomplete cloud-init, independent execution failures, malformed or
  missing artifacts, one-ready/one-failed operation, aggregation failure, and
  case-ambiguous JSON rejection.
- Seven contract mutations reject spend authorization, larger/extra VMs, wide
  ingress, key fingerprint drift, TCP-only promotion, and Round 3 mutation.
- Five Terraform-plan tests reject larger plans, extra resource types, and wide
  ingress, and validate exact create/delete inventories.
- PowerShell recursively validates case-unambiguous JSON and the local external
  key path/fingerprint without printing key material.
- Terraform 1.9.8/provider 2.32.0 passed format, init, validate, and a real
  `-refresh=false` no-apply plan. The exact plan was `3 create / 0 change / 0
  destroy`; its temporary plan, variables, provider cache, and lock file were
  deleted by the gate.
- The full repository control gate passed after the graph mirror, frozen
  negative-result ledger, claim matrix, security, PowerShell syntax, and all
  existing contract gates were synchronized.

No local fixture, plan, public catalog response, or future partial diagnostic is
accepted as R4-405/R4-406 target evidence. VKE remains
`EXTERNAL_VKE_VALIDATION_INCONCLUSIVE`, and R3-325 remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.
