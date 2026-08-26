# R4 VKE Connectivity Diagnostic Attempt 2 (v2 contract)

Date: 2026-08-26 (Asia/Shanghai)

Source revision: `03f22ab836ba3856e88f178237ea6740e8f2d7c0`

Execution ID: `r4-diag-20260826t134703z-03f22ab836`

Approved contract SHA-256:
`1f78b9d3562a6bac3cfa7b9ad070545e5b1eb2c7c9d88090acc9e765c20dc782`

Classification: `DIAGNOSTIC_INCOMPLETE / INSUFFICIENT_EVIDENCE /
CLEANUP_VERIFIED / NO_TARGET_CLAIM`

## Contract and resource boundary

Authenticated preflight selected Vultr `nrt` (Tokyo, JP), VKE
`v1.36.2+1`, one `vhp-4c-8gb-amd` worker and one `vhp-2c-4gb-amd` recovery
observer. The exact plan applied only the approved diagnostic shape: one
recovery firewall, one recovery SSH `/32` rule, one HA VKE with one worker, one
recovery observer, and two VKE API TCP 6443 `/32` rules. No RouteMind,
SigNoz, PVC, Block Storage, Load Balancer, Kubernetes workload, or public
application ingress was created.

Provider readback recorded VKE identity
`42c00adb-f85f-4c86-9b89-be7bf0ae00c9`, endpoint hostname
`42c00adb-f85f-4c86-9b89-be7bf0ae00c9.vultr-k8s.com`, and provider address
`198.13.59.86`. The VKE firewall readback contained exactly the operator and
Tokyo observer IPv4 `/32` TCP 6443 rules. No broad source was used.

## Observations

The Operator probe artifact was written and retained. It preserved the
kubeconfig endpoint identity and hostname SNI, resolved the local synthetic
DNS address, connected TCP 6443, sent TLS ClientHello, and observed
`SSLEOFError` (`DNS_OK / TCP_OK / TLS_EOF / HTTP_NOT_ATTEMPTED`). The probe's
sanitized environment report contained statuses only and no proxy values.

The controller then failed while parsing that JSON artifact because the probe
reported both upper- and lower-case proxy environment names as duplicate JSON
keys. PowerShell `ConvertFrom-Json` rejects keys that differ only by case, so
the failure occurred in phase `operator_probe` before the Tokyo observer probe
could run. Consequently no Tokyo observer artifact or paired readiness
timeline was retained. The failure is recorded verbatim in the external
sanitized artifact `sanitized-evidence/diagnostic-failure.json` with
`failurePhase=operator_probe` and `errorType=InvalidOperationException`.

This is an instrumentation/control-flow defect, not evidence about the VKE
provider. The required differential interpretations remain unauthorized:
neither an operator-only failure, both-observer failure, nor both-observer
success can be claimed.

## Teardown, cost and leakage

The exact destroy plan ran in the controller's `finally` path. Sanitized
cleanup evidence records all four provider identity checks as successful
(`404`), zero remaining execution-label resources, and deletion of kubeconfig
and Terraform runtime state. A residual Terraform state backup was found in
the execution directory and removed by identity-scoped cleanup before evidence
closure. No resource was retained.

The authenticated two-hour quote upper bound was USD 2.20, within the USD 5
incremental ceiling. Adding this attempt to the prior conservative USD 6.60
bound yields USD 8.80, within the approved USD 15 aggregate ceiling. No exact
provider invoice is claimed. The retained sanitized artifacts passed the
forbidden-secret/leakage scan with zero findings.

## Corrective action and disposition

The probe now emits one canonical key per proxy setting while treating Windows
environment names case-insensitively. This prevents PowerShell JSON parser
failure and has a regression test in
`scripts/r4_vke_connectivity_diagnostic_test.py`. The fix is local-only; no
provider call or external retry was performed after the v2 failure.

R4-405 remains `LOCAL_AND_CI_VALIDATED / TARGET_PENDING`; R4-406 remains
`LOCAL_CI_DRILL_VALIDATED / TARGET_PENDING`. No telemetry, DR, production,
provider-root-cause, or target qualification is asserted. The next
discriminating experiment, if separately approved, is a new bounded contract
that runs independent Operator and Tokyo probes even when either probe fails,
retains a phase-labelled result for each observer, and records the full
readiness/backoff ladder. It must use a fresh digest and Human Gate; the v2
digest is consumed and cannot be reused.

R3-325 was not rerun, tuned, reinterpreted, or optimized and remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

## Sanitized artifact digests

The following SHA-256 values identify the retained external artifacts without
including credentials or runtime state:

- `authenticated-quote.json`: `f12be24cc90eca22f3191d474c9e11f3c9890fa56fcecb731ce43d2d6d4dd672`
- `sanitized-evidence/terraform-resource-output.json`: `5d94e7cc6a1fceb4f7f09bccfb2d64ce1a688408497fd9c9b188ccab3d7d078a`
- `sanitized-evidence/firewall-readback.json`: `14bf5f09ae7815405cfd5ed1685792c6596dacbdb679d9c1fa76ca6fac671e5e`
- `sanitized-evidence/operator-connectivity.json`: `442db34ecc77d79b058b60067571ed1797b2f12fa1c1d5f8a4ca390d3e403d2e`
- `sanitized-evidence/diagnostic-failure.json`: `8155d3ff875b37af507566fa9f6366c66c0cbee1f09380187ff58922ff0a6a60`
- `sanitized-evidence/cleanup-inventory.json`: `21ea81f435857a25f43c442dbb422355d0cde6687f8dccef2ab9faf624d82918`
