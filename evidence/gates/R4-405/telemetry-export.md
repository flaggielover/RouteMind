# R4-405 Telemetry Export Evidence

Date: 2026-08-25 (Asia/Shanghai)

Entry revision: `49680bd2cad52244acd44b8f389f62078daa7167`

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
- Final resume after CI closure: PASS. It reports `Current: NONE`, R4-405 and
  R4-406 human/external requirements from their `blocked_by` records, and next
  eligible R4-410/R4-422/R4-437. The former hard-coded `NONE recorded` output
  was removed so the real-time progress capsule remains truthful.
- Implementation `49680bd` passed all five jobs in real GitHub Actions run
  `32852309878`: control/Compose, Java/SBOM/provenance, Python/contracts,
  Web/browser, and resilience/recovery.
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
The contract digest is
`3e320b5b68924bc1a6843f03b0e421116093fb19cf968a649086028d5c71a47d`.

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

This preparation is not target execution. No credentialed provider call ran, no
Vultr resource was created or changed, no spend was authorized, and no target
telemetry or cost evidence exists. R4-405 therefore remains exactly
`LOCAL_AND_CI_VALIDATED / TARGET_PENDING` and blocked at the final
`EXTERNAL EXECUTION HUMAN GATE`.

R3-325 was not rerun, tuned, reinterpreted, or changed. It remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`; this operational telemetry work is not
scientific evidence.
