# R4 Vultr Tokyo External Attempt 3

Date: 2026-08-26 (Asia/Shanghai)

Source revision: `18f9f4f51b72701a39d2ff76c960fa331cd68492`

Execution ID: `r4-ext-20260826t063255z-18f9f4f51b`

Approved contract SHA-256:
`c2a1695104ba7297b51b1c949fa689a4efeb5974dcf1a2122c12f91a57f4e2df`

Classification: `FAILED_EXTERNAL_ATTEMPT / CLEANUP_VERIFIED / NO_TARGET_CLAIM`

## Execution outcome

Authenticated preflight proved Vultr Tokyo `nrt`, VKE `v1.36.2+1`, three
`vhp-4c-8gb-amd` workers, one `vhp-2c-4gb-amd` recovery instance, and the
approved eight-hour/USD 15 boundary. Terraform applied exactly five resources:
one recovery firewall group, one recovery SSH rule, one VKE, one VKE API rule,
and one recovery instance. The VKE and all three worker nodes reached provider
`active` state.

The VKE control-plane firewall group contained exactly one `accept` rule for
the operator `/32` on TCP 6443. The operator public IPv4 remained the approved
address and TCP 6443 was reachable, but the Kubernetes API closed the TLS
connection before handshake. `kubectl`, a kubeconfig client-certificate probe,
and a hostname-preserving TLS probe all observed EOF/timeouts. The bounded
probe was stopped after more than one hour without a successful API response.

No Kubernetes namespace, workload, PVC, SigNoz backend, recovery fixture,
telemetry signal, failure injection, or target DR operation was created. The
Kubernetes mutation marker was absent. No target telemetry, recovery, production,
or cost claim is made.

## Teardown and evidence

The Full execution entered its `finally` teardown path. Terraform reported
`0 added, 0 changed, 5 destroyed`; the provider client then exited while reading
a destroy response stream. The sanitized cleanup inventory nevertheless records
`complete=true`, credentialed checks for VKE, recovery instance, recovery
firewall, and VKE firewall all true, and zero remaining resource IDs. An
independent read-only provider check confirmed all four identities return 404
and the execution label has zero matches.

The local kubeconfig, private-key material, Terraform state/data, and plans were
deleted. Retained non-secret artifacts remain outside Git under
`ROUTEMIND_DATA_ROOT`:

- `authenticated-quote.json`: 653 bytes, SHA-256
  `e7e27574d857fe06d2975fa0bd4cc474936b49d4ef57fcc6124b3ddea457dad9`;
- `sanitized-evidence/terraform-resource-output.json`: 687 bytes, SHA-256
  `7ec06b3b1c0814ca3ac759242cab265bc0d274d76d61232bb5eeae442726b98a`;
- `sanitized-evidence/cleanup-inventory.json`: 411 bytes, SHA-256
  `b7ffd6b42fd5c822efa3c87c8850971861410f331b3ad1580232eda170ef9e02`.

The authenticated eight-hour quote upper bound for this attempt was USD 3.92;
the three-attempt conservative aggregate is USD 4.40 (prior USD 0.48 plus this
attempt's USD 3.92 bound). No CSI block storage was created and provider invoice
settlement is not asserted.

R4-405 and R4-406 remain `LOCAL_AND_CI_VALIDATED / TARGET_PENDING`. R3-325 was
not rerun, tuned, or reinterpreted and remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

## External blocker

The approved operator-only VKE firewall rule was present and matched the
observed operator address, yet the provider VKE control-plane endpoint still
closed TLS before handshake. This is a live provider/network boundary failure,
not evidence that the application or telemetry contract passed. Further paid
execution requires diagnosing this provider endpoint behavior and, if the
resource/network contract changes, a new exact contract digest and Human Gate.

The evidence checkpoint `fd94ce2` passed all five jobs in real GitHub Actions
run `32945284919`, including the control-plane contract gate and independent
recovery drill. This CI result validates the failure/cleanup evidence and does
not qualify the external target.
