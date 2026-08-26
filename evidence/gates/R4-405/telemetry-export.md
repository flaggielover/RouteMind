# R4-405 Telemetry Export Evidence

Date: 2026-08-25 (Asia/Shanghai)

Entry revision: `2efb0f6203752427be6dceb1cddd9ef247082231`

Status: `LOCAL_AND_CI_VALIDATED / TARGET_PENDING`

## Implemented boundary

`contracts/observability/r4-405-telemetry-export-v1.json` freezes the Vultr
`nrt` target, five correlation boundaries, tenant pseudonym and cardinality
policy, logical export-record attribution, application batch limits, collector
queue/retry limits, durable-truth authority, target qualification evidence, and
the frozen scientific boundary. `scripts/telemetry_export_contract.py` validates
the contract and collector structure fail closed; eight mutation groups exercise
identity, target-claim, correlation, tenant leakage, cardinality, collector,
authority, and science drift.

Java owns raw durable tenant identity and derives an HMAC-SHA256 telemetry key.
The key contains only the `rtk_` prefix and 24 digest characters. Metric labels
are bounded to service, signal, operation, and tenant key. The existing HTTP,
message publication, decision, and worker spans now carry bounded correlation
and logical record attribution without using raw tenant identity.

Python accepts only an already pseudonymized key from the private authenticated
Java-to-Python boundary. Invalid or absent keys become `rtk_unattributed`; keys
beyond the default 64-key runtime budget become `rtk_overflow`. W3C context is
injected for message carriers, and simulation and experiment routes create
bounded child spans under the incoming trace.

The candidate Collector config deletes six raw identity attributes and applies
memory limiting, batching, bounded persistent queueing, bounded retry, and
environment-only backend credentials. It is a target-pending configuration,
not evidence of a running collector.

## Durable truth and failure semantics

Python uses `BatchSpanProcessor` for configured production export. A deliberately
failing exporter leaves the tested HTTP business response successful. Telemetry
has no API capable of committing or rolling back PostgreSQL, acknowledging a
RabbitMQ message, mutating Outbox/Inbox state, or changing a business retry.

Application and collector queues are bounded. Overflow or retry exhaustion may
drop telemetry and emit diagnostics. The collector's persistent queue is not a
business durability mechanism. PostgreSQL remains durable truth, Java remains
the consistency authority, and telemetry failure cannot be interpreted as a
business failure.

## Validation state

- Contract validator: PASS. Contract digest
  `f063de18402561caf2fa676a152173395183fc0fe660eebe7b3fe185f32b1d5f`;
  collector digest
  `e1cf3579e04a22cb5210f3f318a123758b4c2b97b7039076507eb27218a36fa7`.
- Contract mutation suite: PASS, 8 tests.
- Focused Python telemetry/tracing tests: PASS, 9 tests. This includes W3C
  message parent continuity, simulation and experiment child correlation,
  tenant overflow/unattributed behavior, and exporter-failure business
  independence.
- Python Ruff format/check and strict mypy: PASS.
- Java full gate: PASS, 113 tests, including architecture, HTTP metric exposure,
  tenant pseudonym/cardinality, message/worker tracing, OIDC, and isolation.
- Python full gate: PASS, 925 tests at 95.09% total coverage; the telemetry
  attribution module is at 100% statement/branch coverage.
- Web gate: PASS, 104 unit tests and production build.
- Full repository gate: PASS, including task graph, Round 4 mirror, contracts,
  security/supply-chain, determinism, analytics, product, agent, recovery,
  release, staged-release, and Compose configuration.
- Serial resilience gate: PASS, 16 Java and 2 Python tests.
- `./scripts/verify.ps1`: PASS after task-control synchronization.
- `./scripts/resume.ps1`: PASS; R4-405 is reported as `validating`, repository
  total remains 165/196, and no task is falsely promoted to passed.
- Final resume after CI closure: PASS. It reports `Current: NONE`, `Next
  eligible: NONE`, and the R4-405/R4-406/R4-410/R4-422 human/external
  requirements from their `blocked_by` records. The former hard-coded `NONE
  recorded` output was removed so the real-time progress capsule remains
  truthful.
- Implementation `49680bd` passed all five jobs in real GitHub Actions run
  `32852309878`: control/Compose, Java/SBOM/provenance, Python/contracts,
  Web/browser, and resilience/recovery.
- Preparation revision `10ec537` passed all five jobs in real GitHub Actions
  run `32920903229`, including the Terraform provider checksum and SigNoz
  Helm offline gate. This validates the preparation checkpoint only; it does
  not qualify a Vultr target or promote R4-405.
- Cross-volume path remediation `a6ca115` plus portable redirect-fixture fix
  `2efb0f6` passed all five jobs in Actions run `32928947867`. Nine path-safety
  tests cover same-volume containment and siblings, cross-volume paths,
  normalized traversal, case/trailing separators, UNC boundaries, device
  namespaces, and symlink/junction rejection.
- Remote control log reports the exact contract digest
  `767ae48b9c377d0718eb28d16fe5539302d2dfc46f66f03e7ca71506fb502395`
  and collector digest
  `b7af884b5f6ad247157dac45da4df448af09e7acbc6ddcb7a758a159404a1b9e`,
  with `collectorVerified:false`, `productionCostVerified:false`, and
  `targetStatus:TARGET_PENDING`.
- The run retained recovery artifact `9564818949`, GitHub digest
  `sha256:f72fd4fdc14119d4a1c893ff31c04a13e495e00815df2f2638b80f4d2f02ae62`.
  This revalidates the separate R4-406 local-CI lane and is not target telemetry
  or target recovery evidence.

## Target qualification still required

R4-405 cannot pass or close from the current evidence. Matching credentialed
Vultr Tokyo evidence must prove:

1. the exact collector, storage, network, backend, and `nrt` identities;
2. trace continuity across HTTP, messaging, workers, simulation, and experiments;
3. a backend leakage scan with no raw tenant or principal identity;
4. observed cardinality, queue saturation, loss, and recovery behavior;
5. an isolated collector/backend outage drill that leaves durable truth intact;
6. backend usage and rate evidence reconciled to tenant-safe logical records.

## Vultr Tokyo execution preparation

The target backend is now selected as self-hosted SigNoz inside Vultr `nrt`.
The selection, exact infrastructure, network/TLS boundary, secret mechanism,
retention, USD 15 / eight-hour execution ceiling, teardown, and 17-check
Evidence Contract are frozen in
`contracts/external-validation/r4-vultr-tokyo-external-validation-v1.json`.
The remediated contract digest is
`4956d29a5cbd69344a70c4d89514608b1acd32924e0598155c7f90848be77393`.

Preparation adds exact Terraform resources, Kubernetes quotas and
NetworkPolicies, two-replica RouteMind Collector deployment, an actual
synthetic Java/Python/Outbox workload plus a separate mTLS OTLP connectivity
probe, pinned SigNoz values, a fail-closed controller, actual ClickHouse signal
queries, evidence leakage scanning, report assembly, and exact teardown
verification. Terraform `1.9.8` validated provider `2.32.0`; Helm `3.18.6`
linted and rendered chart `0.138.0` to 32 objects with no `LoadBalancer`.
Offline mutation tests reject plan expansion, probe-as-backend evidence, secret
leakage, missing signals, target drift, cost drift, cleanup drift, and
scientific promotion.

The current full local rerun passed 113 Java tests, 925 Python tests at 95.09%,
104 Web tests and production build, Playwright 34 passed / 2 expected skips,
and focused resilience 16 Java / 2 Python. The isolated local DR runtime stopped
at an unresponsive Docker Desktop `docker version` before resource creation;
the preparation checkpoint therefore still requires the independent Actions
recovery job rather than treating that local attempt as evidence.

This preparation is not target execution. An authenticated read-only preflight
confirmed the account, Tokyo VKE region, required plan availability, catalog
pricing within the frozen ceiling, VKE versions, and recovery OS without
persisting secret or target evidence. No mutating provider call ran, no Vultr
resource was created or changed, no spend was authorized, and no target telemetry
or cost evidence exists. R4-405 therefore remains exactly
`LOCAL_AND_CI_VALIDATED / TARGET_PENDING` and blocked at the final
`EXTERNAL EXECUTION HUMAN GATE`.

R3-325 was not rerun, tuned, reinterpreted, or changed. It remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`; this operational telemetry work is not
scientific evidence.

## First external attempt and remediation

Approved execution `r4-ext-20260826t042548z-eb70db776c` created exactly the
four planned Vultr `nrt` resources and failed closed before Kubernetes workload
creation when OpenSSL rejected a service DNS name that exceeded the X.509 CN
limit. Exact teardown completed with zero matching provider inventory and no
retained state, kubeconfig, or key material. The conservative one-hour cost
bound is USD 0.24; no provider invoice claim is made. Full sanitized details
are in `evidence/gates/R4-405/2026-08-26-external-attempt-1.md`.

The remediation preserves the resource and USD 15/eight-hour boundaries but
corrects CN/SAN generation, fake-DNS VKE access, failure-stage cleanup, state
backup deletion, provider inventory convergence, and the real TCP 6443 VKE API
boundary. Because the frozen contract digest changed, no second paid execution
is authorized until the new exact digest receives approval. R4-405 remains
`LOCAL_AND_CI_VALIDATED / TARGET_PENDING`.

The remediated implementation passes 6 TLS identity tests including actual
OpenSSL certificate generation, 5 VKE endpoint tests, 4 controller cleanup
guards, 8 contract mutations, offline Terraform/Helm validation, security and
graph controls, Java 113/113, Python 925/925 at 95.09%, and Web 104/104 plus the
production build. These are local preparation results only; real CI and a newly
approved target execution remain mandatory. Remediation revision `fb6adcd`
passed all five jobs in real GitHub Actions run `32934187355`; this validates
the implementation and preparation but does not qualify the external target.

## Second external attempt and VKE firewall remediation

Approved execution `r4-ext-20260826t054111z-ea80181368` reached active Tokyo
VKE and recovery resources, then failed closed before Kubernetes mutation. The
provider-created VKE firewall group had zero rules, so TLS on the otherwise
reachable TCP 6443 endpoint closed before handshake. Terraform teardown and
credentialed zero-inventory checks passed, including a separate read-only 404
for the VKE-managed firewall group. The second-attempt conservative bound is
USD 0.24 and the aggregate two-attempt bound is USD 0.48. Details are in
`evidence/gates/R4-405/2026-08-26-external-attempt-2.md`.

The corrected plan retains the enabled VKE firewall and adds exactly one
operator `/32` TCP 6443 rule. It now has five Terraform resources and records
the VKE firewall group/rule identities for cleanup evidence. The new contract
SHA-256 is
`c2a1695104ba7297b51b1c949fa689a4efeb5974dcf1a2122c12f91a57f4e2df`.
A fresh read-only Terraform plan passed the exact five-create validator and its
temporary plan artifacts were deleted without applying any change. The full
local Java/Python/Web gate and focused contract, controller, Terraform/Helm,
security, graph, and repository controls passed.
Remediation revision `160f670` passed all five jobs in real GitHub Actions run
`32937109761`, including Linux offline Terraform/Helm and independent recovery.
At that stage, no paid execution had been authorized for this digest; R4-405
remained `LOCAL_AND_CI_VALIDATED / TARGET_PENDING`.

## Third external attempt

Execution `r4-ext-20260826t063255z-18f9f4f51b` ran under the approved digest
`c2a1695104ba7297b51b1c949fa689a4efeb5974dcf1a2122c12f91a57f4e2df`. Terraform
applied exactly five resources, including the VKE-managed operator `/32` TCP
6443 rule. VKE and all workers became active, but the API endpoint continued to
close TLS before handshake. The bounded probe was stopped after more than one
hour; no Kubernetes mutation marker, namespace, PVC, collector, backend,
telemetry, or target evidence exists. Full teardown destroyed all five
resources; four provider identities returned 404 and execution-label matches
were zero. Full sanitized detail is in
`evidence/gates/R4-405/2026-08-26-external-attempt-3.md`.

The authenticated eight-hour quote bound was USD 3.92; the conservative
aggregate for all three attempts is USD 4.40. Provider invoice settlement is
not asserted. R4-405 remains `LOCAL_AND_CI_VALIDATED / TARGET_PENDING` pending
provider/network diagnosis; this failure is not an operational pass.
