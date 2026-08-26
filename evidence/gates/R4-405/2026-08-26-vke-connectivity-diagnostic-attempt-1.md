# R4 VKE Connectivity Diagnostic Attempt 1

Date: 2026-08-26 (Asia/Shanghai)

Source revision: `ec5bcf4d6246eb78ccee7e19a49e4027a1f7488a`

Execution ID: `r4-diag-20260826t091304z-ec5bcf4d62`

Approved contract SHA-256:
`30c9580eb2fe43de1306b299a73c4a1c5d0f286ac7bef4be0c3d0f4b7994a426`

Classification: `DIAGNOSTIC_INCOMPLETE / INSUFFICIENT_EVIDENCE /
CLEANUP_VERIFIED / NO_TARGET_CLAIM`

## Contract and resource boundary

The execution used the approved two-hour/USD 5 diagnostic contract, not any
earlier deployment digest. Authenticated preflight selected Vultr `nrt`, VKE
`v1.36.2+1`, one `vhp-4c-8gb-amd` worker and one
`vhp-2c-4gb-amd` observer. The exact plan validator accepted six Terraform
resources: one recovery firewall, one recovery SSH `/32` rule, one VKE with one
worker, one recovery observer, and two VKE API `/32` rules. No RouteMind,
SigNoz, PVC, Block Storage, Load Balancer, Kubernetes workload or public
application ingress was created.

Provider identities were recorded outside Git. The VKE endpoint was
`ce674059-284b-4ac2-a55e-09046f02e501.vultr-k8s.com:6443`, with provider IP
`198.13.59.86`. Firewall readback proved exactly two TCP 6443 accept rules:
the configured operator IPv4 `/32` and the Tokyo observer IPv4 `/32`. There was
no broad source.

## Observations

The operator probe preserved hostname SNI and the kubeconfig endpoint identity.
Local DNS returned a fake-DNS address while the direct connect override used
the provider IP. TCP connected, TLS ClientHello was sent, and the connection
ended with `TLS_EOF`; HTTP was not attempted because TLS did not complete. The
operator route snapshot identified the `Mihomo` TUN interface. This supports a
network-path hypothesis but does not prove the provider-visible source or root
cause.

No Tokyo observer probe artifact or paired retry/backoff record was retained.
The original error occurred after the operator probe and before a paired
readiness record. The controller then performed Terraform destroy; its immediate
404 checks raced provider asynchronous deletion and the teardown error obscured
the original observer-stage error. Because the second required observation is
missing, none of the contract's `operator-only failure`, `both fail`, or `both
succeed` interpretations is authorized. Provider readiness, firewall semantics,
operator/TUN path and observer execution remain unresolved.

## Teardown, cost and leakage

The exact destroy plan was validated and applied. A subsequent credentialed,
read-only provider audit confirmed the VKE, observer, recovery firewall and
provider-managed VKE firewall each return 404, with zero resources matching the
execution label. Kubeconfig, Terraform state and backup, create/destroy plans,
known-host state and provider runtime were deleted. The retained external
artifacts passed a forbidden-secret scan with zero findings.

The authenticated two-hour quote upper bound was USD 2.20, within the USD 5
incremental authorization. Adding that conservative bound to the previous USD
4.40 bound yields USD 6.60 total, within the existing USD 15 aggregate ceiling.
No provider invoice or exact billed amount is claimed.

## Evidence and disposition

Sanitized artifacts remain outside Git under
`ROUTEMIND_DATA_ROOT/external-validation/r4-diag-20260826t091304z-ec5bcf4d62/`.
Their committed digest index covers provider inventory, firewall rules,
operator probe, operator network snapshot, incomplete readiness timeline,
classification, environment versions and cleanup.

R4-405 remains `LOCAL_AND_CI_VALIDATED / TARGET_PENDING`; R4-406 remains
`LOCAL_CI_DRILL_VALIDATED / TARGET_PENDING`. This diagnostic does not qualify
telemetry, DR, production or scientific evidence. R3-325 was not rerun, tuned or
reinterpreted and remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

The consumed digest cannot be reused. Controller remediation adds explicit
observer identity/Python readiness, a writable remote probe destination,
direct retention of sanitized paired artifacts, phase-failure evidence and
bounded asynchronous cleanup convergence. The replacement contract is
`contracts/external-validation/r4-vultr-tokyo-vke-connectivity-diagnostic-v2.json`.
It preserves the exact resource/network shape and requires a new Human Gate.
