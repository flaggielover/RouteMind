# R4 VKE Connectivity Diagnostic Attempt 3 (v3 contract)

Date: 2026-08-26 (Asia/Shanghai)

Source revision: `d0994678492023429a850a78e4104bb71826da5a`

Execution ID: `r4-diag-20260826t145702z-d099467849`

Approved contract SHA-256:
`e1489efe5a21a464389322e29e85da992fee7c0038e4817f4e8392693d16d660`

Classification: `DIAGNOSTIC_INCOMPLETE / INSUFFICIENT_EVIDENCE /
CLEANUP_VERIFIED / NO_TARGET_CLAIM`

## Contract and applied boundary

Authenticated preflight selected Vultr `nrt` (Tokyo, JP), VKE
`v1.36.2+1`, one `vhp-4c-8gb-amd` VKE worker and one
`vhp-2c-4gb-amd` recovery observer. The exact six-resource Terraform plan
created one HA VKE with one worker, one Tokyo observer, one recovery firewall,
one operator SSH TCP 22 `/32` rule, and two VKE API TCP 6443 `/32` rules for
the Operator and Tokyo observer. Firewall readback proved the two VKE rules and
their exact `/32` sources. No `0.0.0.0/0`, RouteMind, SigNoz, PVC, Block
Storage, Load Balancer, Kubernetes workload, or public application ingress was
created.

Provider identity was VKE `7e60e031-9f28-4264-b055-371f599d0206`, endpoint
`7e60e031-9f28-4264-b055-371f599d0206.vultr-k8s.com`, and provider IPv4
`66.42.38.97`. The Tokyo observer IPv4 was `198.13.59.86`. Both resources and
the VKE control-plane state were authenticated as active during the bounded
observation window.

## Independent observations

The Operator and Tokyo observer paths executed, parsed, and persisted through
separate wrappers. Raw output was written before JSON parsing on both paths;
neither path deleted or suppressed the other path's artifacts.

The Operator artifact is canonical schema v2 and `COMPLETE`. Across six
bounded attempts it retained correct endpoint hostname/SNI and kubeconfig
identity, local fake-DNS result `198.18.0.12`, provider connect address
`66.42.38.97`, `DNS_OK`, `TCP_OK`, `TLS_HELLO_SENT`, `TLS_EOF`, and
`HTTP_NOT_ATTEMPTED`. The final terminal classification is `TLS_EOF`. The
operator CIDR did not match the raw TCP source classification, and the WinHTTP
status was `DIRECT`; this preserves a network-path hypothesis without proving
a unique VPN/TUN/CIDR cause.

The Tokyo observer independently produced a raw artifact and a canonical
schema v2 failure artifact on every attempt. Its terminal state was
`EXECUTION_FAILED / OBSERVER_NOT_READY`; DNS, TCP, TLS ClientHello, TLS
handshake, and HTTP stages were therefore `NOT_RECORDED`. The provider
instance readback was `active / running / ok`, but the controller's compound
SSH/cloud-init/identity/Python readiness command never passed. Because that
compound command discarded sub-stage output, the evidence cannot distinguish
SSH reachability/authentication, cloud-init terminal failure, missing identity
file, Python readiness, bootstrap behavior, or shared harness semantics.

The readiness timeline contains six provider-state and paired-summary records.
Since the Tokyo side has no connectivity phase data, v3 is necessarily
`DIAGNOSTIC_INCOMPLETE`. It does not authorize the operator-only, both-failed,
or both-success differential interpretations and does not identify a Vultr,
firewall, endpoint-readiness, VPN/TUN, CIDR, or probe-semantics root cause.

## Teardown, cost, and leakage

The controller applied the exact destroy plan. Credentialed verification then
returned `404` for the VKE, Tokyo observer, recovery firewall, and
provider-managed VKE firewall; execution-label resource count was zero.
Kubeconfig, Terraform state and backup, provider work directory, plan files,
known-hosts material, and runtime variables were deleted. No resource was
retained.

The authenticated two-hour quote upper bound was USD 2.20, below the USD 5.00
incremental ceiling. Adding the prior USD 8.80 conservative bound yields USD
11.00, below the USD 15.00 aggregate ceiling. This is a conservative bound,
not a provider invoice claim.

The retained evidence leakage scan covered 15 runtime and sanitized files and
reported zero secret, raw identifier, and production-data findings. The
post-scan artifact manifest validates all 15 recorded SHA-256 digests and byte
sizes.

## Disposition

R4-405 remains `LOCAL_AND_CI_VALIDATED / TARGET_PENDING`; R4-406 remains
`LOCAL_CI_DRILL_VALIDATED / TARGET_PENDING`. The result supplies neither target
telemetry nor target recovery evidence. No v4 retry or full RouteMind external
validation is authorized or prepared automatically.

If a future experiment is separately designed and approved, its useful
discriminator is independent persistence of the SSH connection, cloud-init
status, identity-file check, and Python check before the Tokyo connectivity
probe. That statement is a next-experiment design observation, not an approval
or root-cause claim.

v1/v2 evidence remains immutable. R3-325 was not rerun, tuned, reinterpreted,
or optimized and remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

## Sanitized artifact digests

- `authenticated-quote.json`: `c205d9b40805f671c841ca8f2d3506148cfffc6d3d01845f62365a9198517ed2`
- `cleanup-inventory.json`: `eaf3df94dc0816c9f9219a1fdb8f1fe0999097a2852a35145f6c2f4e113d4ade`
- `cost-record.json`: `21341d993b31aacdc3ca4cdbf5f65f7a52715ab567585cf6dcc6c3ab95d3f7b1`
- `diagnostic-classification.json`: `0ad761778ac1ad8ae9dae7a4f9b41e38fea283cb163997b7a23a197e1555e362`
- `environment-version-manifest.json`: `50bd12b18bd50a745de98266e7726daa0088fa4a143081cf2e4faa6ae49499b7`
- `firewall-readback.json`: `eba078e087e8a85471fd6a1bc7fd678c33ad0ee9bccca9b8d0078716abaafeae`
- `leakage-scan.json`: `e9bbd738dd368cdd5ed46425b87a5f16006882df46877aae32de2c678d40dda3`
- `observer-readiness-diagnostic.json`: `16bedde839e1c7d7e0e2016999ffbcff825cc0c2bc5eea580c1f76f5fa1bd0f1`
- `operator-connectivity.json`: `433edc3685a147bd74ae5af0212b78558278e880f12c7fc42b285385a9b22e12`
- `operator-connectivity.raw`: `d6d00762abc9d4206aa58bc1d84f7189689aa5023a0193ac99587a3960e1b202`
- `operator-network-snapshot.json`: `719afb93d2a6ece4fcb7947c72e76519a8f3d8dc590652adffb2f9bbc4de2f19`
- `readiness-timeline.json`: `cd031ad34da5358439c5b4617e594a7d047332e1cddb63f7c2a0cadb69bc406e`
- `terraform-resource-output.json`: `2e46bb1ac6c89eaaa25cfc03611742a4d8f16e35a235f4daf7082881470f80ec`
- `tokyo-recovery-connectivity.json`: `53236b29d90c1502a541082a19de97c6176d555c8d733dbd5604a1f315013e7d`
- `tokyo-recovery-connectivity.raw`: `7eb70257593da06f682a3ddda54a9d260d4fc514f645237f5ca74b08f8da61a6`
