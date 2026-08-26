# R4 Vultr Tokyo External Attempt 1

Date: 2026-08-26 (Asia/Shanghai)

Source revision: `eb70db776ca0460d9dec22484212487d95b84e4a`

Execution ID: `r4-ext-20260826t042548z-eb70db776c`

Approved contract SHA-256:
`3e320b5b68924bc1a6843f03b0e421116093fb19cf968a649086028d5c71a47d`

Classification: `FAILED_EXTERNAL_ATTEMPT / CLEANUP_VERIFIED / NO_TARGET_CLAIM`

## Execution outcome

The authenticated quote proved Vultr Tokyo `nrt`, one HA VKE with three
`vhp-4c-8gb-amd` workers, one `vhp-2c-4gb-amd` recovery instance, the exact
firewall boundary, an eight-hour maximum, and a USD 3.92 execution quote below
the approved USD 15 ceiling. Terraform then created exactly four planned
resources: the VKE, recovery instance, recovery firewall group, and one SSH
allowlist rule.

The run failed closed before any Kubernetes namespace, workload, PVC, telemetry
backend, or recovery fixture was created. The first local retry needed the
already-installed Git for Windows OpenSSL on `PATH`. After VKE provisioning,
the local fake-DNS resolver required the provider-returned control-plane IP
while retaining kubeconfig CA and hostname validation. Certificate generation
then rejected the SigNoz service DNS name as an X.509 Common Name longer than
64 bytes. The name belonged in SAN with a short CN.

Teardown initially encountered a transient Kubernetes API EOF and then Vultr
list eventual consistency. Recovery used only the same exact Terraform state.
It destroyed all four resources, verified the VKE, recovery instance, and
firewall identities as absent, verified zero matching execution labels, removed
the kubeconfig, generated keys, Terraform state/data, and the residual state
backup, and retained only sanitized non-secret attempt metadata.

## Cost and retained artifacts

The bounded window was `2026-08-26T04:25:50Z` through cleanup verification at
`2026-08-26T04:59:48Z`. At the frozen hourly rates, the prorated compute bound
is below USD 0.14; conservatively rounding the attempt to one billed hour gives
an upper bound of USD 0.24. No CSI block storage was created. Provider invoice
settlement was not asserted.

Large/local artifacts remain outside Git under `ROUTEMIND_DATA_ROOT`:

- `authenticated-quote.json`: 653 bytes, SHA-256
  `2901b20efd690e6eab24bb9fb58487e5433176ba1054c5ae28131367d9d635e8`;
- `sanitized-evidence/cleanup-inventory.json`: 385 bytes, SHA-256
  `e004103464a74b72dc458cd36aa7ef035b64cab2d6cbed4b54625d055ec746ef`.

No secret value, private key, kubeconfig, Terraform state, raw tenant identity,
or production data is retained in this evidence. R4-405 and R4-406 remain
target-pending. R3-325 was not rerun and remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

## Remediation gate

The controller now separates short X.509 CNs from full DNS SANs, tests the
OpenSSL certificate path, repairs only the `198.18.0.0/15` fake-DNS case with
the authenticated provider IP while preserving TLS hostname verification,
marks actual Kubernetes mutation before requiring in-cluster teardown, removes
Terraform state backups, and retries exact provider inventory convergence.

The corrected network contract distinguishes the Vultr REST API on TCP 443
from the VKE Kubernetes API on TCP 6443. This material correction creates a new
contract SHA-256 and requires a new approval before another paid execution.
