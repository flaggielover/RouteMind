# Tokyo VM External Validation v2 Attempt 1

## Classification

This is immutable external-execution evidence for the approved no-new-VPC
contract. Provisioning and exact cleanup succeeded, but secure bootstrap did not.
The result is `FAIL / TARGET_PENDING`, not target, production, VKE, telemetry, or
DR validation.

```text
contract = r4-vultr-tokyo-vm-external-validation-v2
contract_sha256 = b1cf89b905b6bb42a98eba17de31fb21883ed94139301986a06247acc660a05b
execution_id = r4-vm-v2-20260827t051846z-7c7bd60337
source_revision = 7c7bd6033745a7301172ab96bf3d3fbc2dc1c64a
region = nrt
result = FAIL
terminal_phase = secure_bootstrap
```

## Preflight and provision

- The invalid Prometheus indentation in the approved runtime Collector YAML was
  found before resource creation, corrected without changing the contract
  resource/network/cost boundary, and covered by a directed regression plus real
  Collector `0.159.0` validation. Commit `7c7bd60` passed all five jobs in
  GitHub Actions run `33041893437`.
- Authenticated preflight proved Vultr `nrt` / Tokyo, Ubuntu 24.04 x64, the two
  exact VM plans, the configured provider SSH key identity, operator IPv4 `/32`,
  zero prior v2 execution resources, and a six-hour USD 1.476 upper quote under
  the USD 3 ceiling.
- Saved plan SHA-256
  `5521bfa1308229aa40a6908ae634bf00c30dc75e7fd37cdf728c85ff778054ac`
  contained exactly two VM, one firewall-group, and two firewall-rule creates:
  `5 create / 0 change / 0 destroy / 0 VPC`.
- Provider readback proved primary `41290d1b-1300-4822-91d8-283fc85798d6`
  (`vc2-8c-32gb`), recovery `8a8942db-b866-4cec-a57e-95af0dd58a1e`
  (`vc2-2c-4gb`), and firewall group
  `7d7c5cbe-7687-4d27-95df-0e1fbca1fe8f` in the approved boundary. The two
  ingress rules were exact IPv4 `/32` TCP 22 rules. No VPC, block storage, load
  balancer, VKE, public application, OTLP, or SigNoz endpoint was created.

## Fail-closed bootstrap result

Both instances reached provider state `active / ok / running`. The direct
operator egress identity matched the approved firewall source, both TCP 22
connections completed, and provider firewall readback matched both exact rules.
Both hosts nevertheless closed before an SSH server banner / key exchange could
be retained (`kex_exchange_identification` / empty server banner).

One bounded recovery-VM reboot was performed without changing resource shape,
network exposure, or cost. The recovery instance returned to
`active / ok / running`, but its SSH result remained unchanged. No firewall was
widened and no second paid attempt was started. The evidence does not identify a
unique image, sshd, provider-network, firewall, operator, VPN/TUN, or timing root
cause.

Secure bootstrap, RouteMind, SigNoz, OTLP traces/metrics/logs, telemetry failure
injection, encrypted cross-VM transfer, restore, reconciliation, and DR were not
executed. Partial infrastructure success is not target evidence.

## Teardown, cost, and leakage

- Exact destroy plan SHA-256
  `f0a715dd0904e2eb056c7ca99e7112e555009d9b2fcd1f90ce24223b3e4c292b`
  passed the delete-only gate: `0 create / 0 change / 5 destroy / 0 VPC`.
- Both VM identities and the firewall identity returned HTTP 404 after teardown;
  execution-label inventory was zero. The five pre-existing `nrt` VPCs were not
  modified or deleted.
- The conservative one-hour incremental bound is USD 0.246. The cumulative
  conservative external bound recorded by the contract is USD 11.246, below its
  aggregate ceiling.
- Terraform state, plans, provider cache, vars, raw resource output, and any
  private execution state were deleted. Only sanitized evidence remains under
  `ROUTEMIND_DATA_ROOT/external-validation/r4-vm-v2-20260827t051846z-7c7bd60337/`.
- Tracked-repository plus sanitized-artifact leakage scan found zero secrets.
  Artifact-manifest SHA-256 is
  `a67384b4b6fdaeee6a1738a7abaf47a1e6f9eafc70e03af206bedada26f1dcf6`.

R4-405 remains `LOCAL_AND_CI_VALIDATED / TARGET_PENDING`; R4-406 remains
`LOCAL_CI_DRILL_VALIDATED / TARGET_PENDING`. The v2 digest is consumed and may
not be reused. A paid follow-up requires a new contract, digest, and Human Gate.
VKE remains `EXTERNAL_VKE_VALIDATION = INCONCLUSIVE`, with `NO_TARGET_CLAIM` and
`NO_ROOT_CAUSE_CLAIM`. R3-325 remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.
