# R4 Vultr Tokyo External Attempt 2

Date: 2026-08-26 (Asia/Shanghai)

Source revision: `ea80181368ba1a77ac1b5b462c6150e1f4345975`

Execution ID: `r4-ext-20260826t054111z-ea80181368`

Approved contract SHA-256:
`4956d29a5cbd69344a70c4d89514608b1acd32924e0598155c7f90848be77393`

Classification: `FAILED_EXTERNAL_ATTEMPT / CLEANUP_VERIFIED / NO_TARGET_CLAIM`

## Execution outcome

The authenticated preflight again proved Vultr Tokyo `nrt`, one HA VKE with
three `vhp-4c-8gb-amd` workers, one `vhp-2c-4gb-amd` recovery instance, an
eight-hour maximum, and a USD 3.92 quote. Including the first attempt's
conservative USD 0.24 bound, the aggregate authorized ceiling remained safe.
Terraform created exactly the approved four-resource plan and all target
compute resources reached provider `active` state.

The VKE API remained unreachable after TCP connect. Credentialed provider
inspection showed that `enable_firewall=true` had created a distinct VKE
control-plane firewall group with zero rules. The configured operator CIDR
matched the observed operator public `/32`; the VKE, all three nodes, and TCP
6443 were active/reachable, but TLS was closed before handshake because no VKE
API allowlist rule existed. No Kubernetes namespace, workload, PVC, telemetry
backend, recovery fixture, or target data was created.

The run was stopped rather than disabling the VKE firewall, adding an unapproved
rule, opening a broad port range, or weakening TLS. Exact Terraform teardown
destroyed the VKE, recovery instance, recovery firewall group, and SSH rule.
The controller verified its three recorded provider identities and zero matching
execution labels; a separate credentialed read-only check also verified the
provider-managed VKE firewall group as absent. Local Terraform state/data,
kubeconfig, plans, and generated secrets were deleted.

## Cost and retained artifacts

The resources existed for less than one hour. At the authenticated hourly rates,
the conservative second-attempt upper bound is USD 0.24; the aggregate bound for
attempts 1 and 2 is USD 0.48. No CSI block storage was created. Provider invoice
settlement is not asserted.

Large/local artifacts remain outside Git under `ROUTEMIND_DATA_ROOT`:

- `authenticated-quote.json`: 653 bytes, SHA-256
  `3a91890f8690b3f2215e24c62d20da279b74c177569507f7579276507d444d8e`;
- `sanitized-evidence/cleanup-inventory.json`: 385 bytes, SHA-256
  `59ed4b282e6b73eb304d6268b2b56643936004fc58f1cd38711b771f8a69c8b1`.

No secret, private key, kubeconfig, Terraform state, raw tenant identity, or
production data is retained. R4-405 and R4-406 remain target-pending. R3-325 was
not rerun and remains exactly `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

## Remediation gate

The remediated Terraform inventory adds one operator `/32` TCP 6443 rule to the
VKE-managed firewall group while retaining `enable_firewall=true`. The exact
plan is now one recovery firewall group, two narrow firewall rules, one recovery
instance, and one VKE. The controller records the VKE firewall group/rule
identities and verifies the group is absent after VKE deletion. This material
resource-shape correction changes the contract digest and requires a new Human
Gate before any further paid execution.

A fresh read-only Terraform plan passed the exact resource validator with five
creates and no resource mutation. The temporary plan was deleted. The complete
local gate then passed Java 113/113, Python 925/925 at 95.09% coverage, Web
104/104 plus production build, contract/controller tests, Terraform/Helm,
security, graph, and repository controls. Remediation revision `160f670` then
passed all five jobs in real GitHub Actions run `32937109761`, including the
Linux offline Terraform/Helm gate and independent recovery drill. This CI result
validates preparation only and does not qualify the external target.
