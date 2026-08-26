# RouteMind R4 VKE TLS EOF Diagnostic

## Frozen terminal disposition (2026-08-27)

The owner stopped further VKE diagnostic design and execution. The complete v1,
v2, and v3 record is immutable and closes with:

```text
EXTERNAL_VKE_VALIDATION = INCONCLUSIVE
R4-405 / R4-406 = TARGET_PENDING
NO_TARGET_CLAIM
NO_ROOT_CAUSE_CLAIM
```

No v4 may be designed or executed under this diagnostic line. Historical attempt,
failure, cost, and teardown evidence must not be deleted, overwritten, or
reinterpreted. A separate platform-neutral Tokyo VM qualification may test the
original R4-405/R4-406 properties, but it cannot change this VKE disposition or
claim VKE validation.

Date: 2026-08-26 (Asia/Shanghai)

Status: `DIAGNOSTIC_PREPARED / ROOT_CAUSE_UNKNOWN / NO_RESOURCE_MUTATION`

This report audits the third external attempt without changing its frozen
evidence. It contains no credentials, private-key material, kubeconfig
contents, or secret values. The diagnostic itself used only local inspection,
read-only provider calls, and direct socket probes.

## Frozen facts and attempt audit

The audited attempt was
`r4-ext-20260826t063255z-18f9f4f51b`, source revision
`18f9f4f51b72701a39d2ff76c960fa331cd68492`, under the previously approved
contract digest
`c2a1695104ba7297b51b1c949fa689a4efeb5974dcf1a2122c12f91a57f4e2df`. That
digest has already been consumed and is not reusable.

The Terraform configuration in
`infra/external-validation/vultr-tokyo/main.tf` creates one recovery firewall
group, one recovery SSH rule, one HA VKE with three workers, one provider-managed
VKE firewall rule, and one recovery host. The output inventory recorded the
following non-secret identities: VKE `4181e71c-82c4-431e-ae99-9070179e0bce`,
provider VKE firewall `7921c018-1d20-4631-96f8-259c7e940466`, recovery firewall
`26f016f5-ff1c-4ff7-918e-bade8dc1a510`, and recovery host
`60a70175-61a2-4fc1-83fb-89cd55fde59d`. The VKE endpoint hostname was
`4181e71c-82c4-431e-ae99-9070179e0bce.vultr-k8s.com`, with provider-returned
IPv4 `66.42.38.97`.

The controller's endpoint helper accepts HTTPS only, detects the local
`198.18.0.0/15` fake-DNS range, rewrites the kubeconfig server to the
provider-returned IPv4, and preserves the original hostname as TLS server name.
It does not alter the CA or client credentials. The provision path then calls
`kubectl get nodes` in a 60-attempt loop with ten-second sleeps. That call has no
per-request timeout and the loop records no phase-labelled DNS/TCP/TLS/HTTP
artifact. The third attempt therefore demonstrated that provider resource
`active` is not equivalent to an externally ready Kubernetes API, but it did
not isolate the cause.

The retained timestamps are execution start `2026-08-26T06:32:56Z`, quote
observation `2026-08-26T06:33:15Z`, and cleanup verification
`2026-08-26T07:34:45Z`. Exact provider resource-creation timestamps were not
retained in the sanitized inventory and are not inferred here. Historical
`kubectl`, client-certificate TLS, and hostname-preserving TLS probes observed
EOF or timeout before handshake. No Kubernetes mutation marker existed.

Teardown reported five destroys and the sanitized cleanup inventory is
`complete=true`; independent read-only checks returned 404 for all four named
identities and zero execution-label matches. The original attempt evidence and
its hashes remain authoritative.

## Endpoint semantics

| Check | Observation | Interpretation |
| --- | --- | --- |
| Scheme | `https` | Matches the VKE API contract. |
| Port | `6443` | No duplicated-port or protocol mismatch was found. |
| Provider hostname | `4181e71c-82c4-431e-ae99-9070179e0bce.vultr-k8s.com` | Comes from the Terraform output inventory. |
| Current DNS A | `198.18.0.40` | Local fake-DNS answer; not a routable provider address. |
| Current DNS AAAA | none observed | No IPv6 preference evidence. |
| Provider address | `66.42.38.97` | Public IPv4 used only as a diagnostic connect override. |
| Kubeconfig relationship | Historical helper rewrote only the server address and preserved the hostname as SNI | SNI-preserving behavior is supported by code and tests; the deleted kubeconfig cannot be re-read. |
| Public/private | Provider address is public IPv4; DNS answer is synthetic fake-DNS | Endpoint is intended to be public, but the local resolver path is intercepted. |

The current direct probe sent a TLS ClientHello to both the provider-IP
override and the fake-DNS address with SNI set to the provider hostname. Both
had `TCP_OK` and `TLS_HELLO_SENT`; neither reached HTTP and the provider-IP
probe ended `TLS_TIMEOUT`. This is new diagnostic evidence, not target
qualification and not proof that the provider endpoint is defective.

## Firewall semantics

The third-attempt provider readback showed the VKE-managed firewall group
`7921c018-1d20-4631-96f8-259c7e940466` with exactly one `accept` rule: TCP
6443, IPv4, source `48.47.19.5/32`, rule id `1`. That source matched the
`ROUTEMIND_OPERATOR_CIDR` value and the `api.ipify.org` HTTP result at the time
of provisioning. The recovery firewall was a separate group with an SSH-only
rule. No recovery-host rule was used to stand in for the VKE control-plane
boundary, and no worker-node firewall was treated as the control-plane rule.

The rule was read back from the provider API rather than inferred from
Terraform state. No broad source, IPv6 rule, or public load-balancer rule was
observed. Provider-side implicit ordering or an undocumented control-plane
policy is not visible from the retained evidence and remains unknown.

## Operator egress, VPN, and proxy

The diagnostic environment reported all eight conventional proxy environment
variables as `MISSING`. WinHTTP reported `DIRECT`. The .NET default proxy
object existed without a configured URI and reported `api.vultr.com` as not
bypassed, so PowerShell/.NET proxy behavior is not equivalent to the direct
socket path.

The active raw-TCP interface was `Mihomo` (a TUN adapter); the preferred
default route was WLAN. A direct Python socket to `66.42.38.97:6443` reported
`TCP_OK`, but its local source address classified as `FAKE_DNS` and did not
match the configured operator `/32`. In contrast, the HTTP `api.ipify.org`
result did match the configured `/32`. This proves that the HTTP egress address
is not sufficient evidence for the raw 6443 source path. The exact raw source
address is deliberately not retained in this report.

This is the strongest current evidence for a local VPN/TUN or raw-TCP routing
mismatch, but it is not a root-cause claim: a successful TCP connect followed
by a TLS timeout can still be caused by the remote endpoint or an intermediary.

## TLS probe audit

The new read-only tool `scripts/r4_vke_connectivity_diagnostic.py` performs
separate stages:

`DNS_OK/DNS_FAIL -> TCP_OK/TCP_FAIL -> TLS_HELLO_SENT -> TLS_OK/TLS_EOF/TLS_RESET/TLS_TIMEOUT/TLS_CERT_FAILURE -> HTTP_OK/HTTP_FAIL`.

It uses a direct `socket` connection, passes the provider hostname as SNI even
when a provider-IP override is used, never sends credentials, and does not
consult an HTTP proxy. It distinguishes EOF, reset, timeout, certificate
failure, and generic TLS errors. The current provider-IP run produced
`DNS_OK`, `TCP_OK`, `TLS_HELLO_SENT`, `TLS_TIMEOUT`, and no HTTP request. The
historical failure was EOF/timeout before handshake; no certificate-validation
failure was observed.

## Readiness timing finding

The existing controller waits for Terraform completion and then immediately
starts a `kubectl get nodes` loop. It does not separately record provider
state, endpoint population, DNS propagation, TCP reachability, TLS handshake,
or HTTP `/version`; an individual `kubectl` call can also exceed the intended
ten-second cadence because it lacks `--request-timeout`. Fixed sleeps are not
readiness evidence.

The prepared diagnostic contract defines this bounded ladder:

1. provider cluster state is `active`;
2. endpoint hostname and provider IP are present;
3. DNS A/AAAA results are recorded;
4. TCP 6443 is tested from each observer;
5. TLS ClientHello and handshake use hostname SNI;
6. unauthenticated HTTP `/version` is attempted without mutation.

The ladder uses 2/4/8/16/32-second capped backoff with a 20-minute deadline.
Each probe is timestamped; no fixed sleep can substitute for a successful
stage.

## Differential diagnosis matrix

| Candidate | Supporting evidence | Contradicting evidence | Confidence | Next discriminating test |
| --- | --- | --- | --- | --- |
| A. Wrong endpoint | Local DNS is synthetic and kubeconfig needed an IP rewrite | Hostname and provider IP came from the same Terraform output; SNI was preserved | Low/medium | Provider-side endpoint readback plus `/version` from both observers |
| B. Endpoint not ready | Resource `active` did not imply API readiness; no explicit readiness ladder existed | More than one hour of attempts still failed | Medium | Bounded repeated TLS/HTTP probes with provider-state timestamps |
| C. Wrong firewall attachment/rule | Prior attempts exposed a zero-rule provider VKE group | Third attempt read back the correct VKE group with exact TCP 6443 `/32` rule | Low | Read back rule from provider and test from an independent Tokyo source |
| D. Operator CIDR mismatch | Configured `/32` matched HTTP `api.ipify` but not raw-TCP source classification | Source address is not retained as a public value; TCP was reachable | Medium | Run raw socket from a non-TUN path and compare provider rule source |
| E. VPN/proxy/raw-TCP mismatch | `Mihomo` TUN carried the raw path; direct probe source classified `FAKE_DNS`; .NET proxy bypass differed | Conventional proxy variables and WinHTTP were direct | Medium/high | Disable/bypass TUN for one bounded probe, or compare Tokyo recovery observer |
| F. Upstream ISP/network blocks 6443 | TLS timeout after ClientHello is compatible with filtering | TCP 6443 reached the provider address | Low/medium | Same endpoint from Tokyo recovery host and a direct operator path |
| G. IPv4/IPv6 mismatch | AAAA was absent in current DNS | Provider IPv4 path was explicitly tested | Low | Record both families from both observers in the new ladder |
| H. TLS/SNI/probe defect | Any custom probe can be wrong | New tool uses direct sockets and correct hostname SNI; kubectl and two TLS probes agreed | Low | Compare `openssl s_client -servername` and native probe with same timeout |
| I. Vultr/VKE provider-side issue | Repeated pre-handshake EOF/timeout after active state and correct rule | No independent Tokyo-side observation exists | Medium | Tokyo recovery observer to the same hostname/IP, then provider support evidence if both fail |
| J. Other | Incomplete provider/intermediary telemetry | No additional evidence | Unknown | Capture bounded phase-labelled traces without secrets |

No candidate is promoted to root cause. The current disposition is
`UNKNOWN`, with E/D/B/I as the highest-value discriminating branches.

## Minimal corrective contract

The new prepared contract is
`contracts/external-validation/r4-vultr-tokyo-vke-connectivity-diagnostic-v1.json`.
Its canonical SHA-256 is
`30c9580eb2fe43de1306b299a73c4a1c5d0f286ac7bef4be0c3d0f4b7994a426`.
It superseded, but did not reuse, the consumed validation digest. That digest
was later consumed once by the approved diagnostic execution below.

The contract is fail-closed and currently unauthorized. If approved later, it
would create only one minimal HA VKE with one worker, one two-hour recovery
observer, one recovery firewall, and two exact provider-managed VKE API `/32`
rules (operator and recovery observer). It creates no RouteMind workload,
SigNoz, PVC, block storage, load balancer, public application ingress, or
telemetry persistence. The recovery observer is necessary because it separates
the operator/TUN/ISP path from a Tokyo-to-control-plane path.

The proposed incremental ceiling is USD 5.00, two hours maximum, with the
previous USD 4.40 conservative bound carried into the USD 15 aggregate ceiling.
The execution would stop on any resource/rule drift, secret/output leakage,
unexpected Kubernetes mutation, deadline/cost breach, or unprovable cleanup.
Teardown is identity-scoped: remove the two API rules, destroy VKE and the
observer, destroy the recovery firewall, verify exact 404s and zero execution
labels, then delete local kubeconfig/state/key material.

Expected evidence is limited to authenticated Tokyo/resource identity,
firewall readback, endpoint semantics, operator and Tokyo phase-labelled
probes, readiness timeline, sanitized environment/network manifest, and exact
cleanup. It cannot qualify R4-405/R4-406 and cannot alter the frozen Round 3
result.

## Local validation and gate

The diagnostic tool has eight regression tests covering endpoint parsing, fake
DNS/public/private classification, CIDR matching, TLS error distinctions,
kubeconfig server extraction, SNI preservation, and multi-server rejection.
The new contract validator rejects identity, scope, resource, firewall,
endpoint, readiness, cost, teardown, evidence, and scientific-boundary drift.
No provider mutation was performed while preparing this report.

Commit `98b287734c058006569c2d5c5961c0cb2ffdfd25` passed all five jobs in real
GitHub Actions run `32948600781`, including the control-plane preparation,
Python contract, Java, web, and resilience jobs. CI success validates the
diagnostic preparation only; it does not qualify a Vultr target.

## Approved attempt and replacement gate

Execution `r4-diag-20260826t091304z-ec5bcf4d62` used the approved digest
`30c9580e...4a426` exactly once and the exact six-resource/two-`/32` shape.
Operator evidence recorded `DNS_OK / TCP_OK / TLS_EOF`; the Tokyo observer
artifact was not recorded before teardown. The result is therefore
`DIAGNOSTIC_INCOMPLETE / INSUFFICIENT_EVIDENCE`, with no root-cause branch or
target claim authorized. Exact teardown later proved four provider identities
`404` and zero execution-label matches; sensitive runtime artifacts were
deleted and retained files had zero leakage findings. Full detail is in
`evidence/gates/R4-405/2026-08-26-vke-connectivity-diagnostic-attempt-1.md`.

The consumed digest cannot be reused. Controller remediation preserves the
same resource shape while requiring observer identity/Python readiness, direct
sanitized-artifact retention, phase-failure evidence, and bounded asynchronous
cleanup convergence. Replacement contract
`contracts/external-validation/r4-vultr-tokyo-vke-connectivity-diagnostic-v2.json`
has canonical SHA-256
`1f78b9d3562a6bac3cfa7b9ad070545e5b1eb2c7c9d88090acc9e765c20dc782` and awaits
a new **VKE TLS EOF DIAGNOSTIC RETRY HUMAN GATE**. Until approved, no paid
resource execution is authorized.

## Approved v2 diagnostic execution

Execution `r4-diag-20260826t134703z-03f22ab836` ran under the approved v2
contract digest
`1f78b9d3562a6bac3cfa7b9ad070545e5b1eb2c7c9d88090acc9e765c20dc782`.
Authenticated preflight and Terraform readback proved the exact Tokyo
six-resource shape and two `/32` TCP 6443 rules. The Operator probe retained
`DNS_OK / TCP_OK / TLS_EOF / HTTP_NOT_ATTEMPTED` with hostname SNI. Before the
Tokyo observer probe could run, PowerShell rejected the probe JSON because
case-variant proxy names were duplicate keys. The run therefore remains
`DIAGNOSTIC_INCOMPLETE / INSUFFICIENT_EVIDENCE`; no provider, VPN/TUN, or
readiness root cause is promoted.

The controller completed exact teardown: four provider identities returned
`404`, execution-label inventory was zero, and a residual Terraform backup was
removed by identity-scoped cleanup. The attempt quote bound was USD 2.20 and
the conservative aggregate bound is USD 8.80 within the approved USD 15 cap;
no invoice claim is made. Retained sanitized artifacts had zero leakage
findings. The probe now emits unique case-insensitive proxy keys with a
regression test. Any further differential experiment requires a fresh bounded
contract and Human Gate; the v2 digest is consumed. R4-405/R4-406 remain
target-pending, and R3-325 remains frozen at
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

## Prepared v3 independent-artifact contract

The v2 parser defect is fixed, but its evidence remains immutable and its
digest `1f78b9d3562a6bac3cfa7b9ad070545e5b1eb2c7c9d88090acc9e765c20dc782`
cannot be reused. The prepared v3 contract is
`contracts/external-validation/r4-vultr-tokyo-vke-connectivity-diagnostic-v3.json`
with canonical SHA-256
`e1489efe5a21a464389322e29e85da992fee7c0038e4817f4e8392693d16d660`.

Its sole diagnostic objective is to persist independent Operator and Tokyo
observer artifacts for the same VKE endpoint. Each artifact uses canonical
schema version 2 with exact phase records for DNS, resolved IP, TCP, TLS
ClientHello, TLS handshake, and HTTP/Kubernetes API, plus timestamps, retries,
and terminal error classification. Raw probe output is written before parsing;
execution, malformed JSON, missing artifact, and aggregation failures each
produce a fail-closed artifact without deleting the other observer's evidence.
Readiness is bounded and records provider state and first-success/failure
timestamps. Local regression tests inject all six required single-point
failures, including malformed Operator/Tokyo output, both execution failures,
aggregation failure, and one-side missing data.

The resource and network boundary is unchanged: one minimal Tokyo HA VKE with
one worker, one Tokyo recovery observer, one recovery firewall, one operator
SSH `/32`, and two exact VKE API TCP 6443 `/32` rules. No RouteMind/SigNoz
workload, PVC, Block Storage, Load Balancer, or public application ingress is
allowed. The v3 contract allows at most two hours and USD 5 incremental cost;
prior conservative spend is USD 8.80 and the aggregate ceiling is USD 15.00.
No Vultr resource was created, modified, or deleted while preparing v3.

The contract is stopped at `VKE CONNECTIVITY DIAGNOSTIC V3 HUMAN GATE`.
R4-405/R4-406 remain `LOCAL_AND_CI_VALIDATED / TARGET_PENDING`; this
preparation cannot qualify telemetry or disaster-recovery evidence. R3-325
remains exactly `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.

## Approved v3 diagnostic execution

Execution `r4-diag-20260826t145702z-d099467849` consumed approved v3 digest
`e1489efe5a21a464389322e29e85da992fee7c0038e4817f4e8392693d16d660`
exactly once. The exact Tokyo six-resource shape and three `/32` rules applied,
with no workload, persistent storage, load balancer, or public application
ingress. The Operator raw and canonical artifacts were retained independently
and recorded `DNS_OK / TCP_OK / TLS_EOF / HTTP_NOT_ATTEMPTED` across six
attempts with correct hostname SNI.

The Tokyo path also retained independent raw and canonical failure artifacts,
but its compound SSH/cloud-init/identity/Python readiness check never passed.
Its terminal state is `EXECUTION_FAILED / OBSERVER_NOT_READY`, with all
connectivity phases `NOT_RECORDED`. Provider readback showed the instance and
VKE active, but the evidence cannot distinguish the readiness sub-stages.
Therefore v3 is `DIAGNOSTIC_INCOMPLETE / INSUFFICIENT_EVIDENCE`; it does not
authorize any operator-only, both-failed, both-success, provider, firewall,
VPN/TUN, CIDR, readiness, or shared-probe root-cause conclusion.

Teardown returned four exact provider `404` results and zero execution-label
resources. All runtime state was removed. The incremental conservative upper
bound is USD 2.20 and the cumulative bound is USD 11.00 within the USD 15
ceiling. Fifteen retained files passed the leakage scan with zero findings and
their digests validate. Full detail is in
`evidence/gates/R4-405/2026-08-26-vke-connectivity-diagnostic-attempt-3.md`.

No v4 retry or full RouteMind external validation is authorized. A future
experiment would need a fresh design and Human Gate that independently records
each Tokyo readiness sub-stage. R4-405/R4-406 remain target-pending; R3-325
remains exactly `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.
