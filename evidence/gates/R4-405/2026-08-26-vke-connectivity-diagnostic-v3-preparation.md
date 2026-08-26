# R4 VKE Connectivity Diagnostic v3 Preparation

Date: 2026-08-26 (Asia/Shanghai)

Status: `PREPARED / HUMAN_GATE_REQUIRED / NO_EXTERNAL_EXECUTION`

Contract: `contracts/external-validation/r4-vultr-tokyo-vke-connectivity-diagnostic-v3.json`

Canonical contract SHA-256:
`e1489efe5a21a464389322e29e85da992fee7c0038e4817f4e8392693d16d660`

## Purpose

v3 is limited to one scientific/engineering question: obtain two independent,
phase-labelled artifacts for the same VKE hostname and provider IP, even when
one observer fails. v1 and v2 evidence remain immutable. The v2 direct cause
(PowerShell rejection of duplicate case-variant proxy keys) is fixed in the
probe and covered by regression tests; no provider, VPN/TUN, firewall, or
readiness root cause is inferred from that fix.

## Independent artifact contract

The canonical probe schema is version 2 with exact case-sensitive top-level
keys, observer identities `operator` and `tokyo-recovery`, and phases `dns`,
`tcp`, `tls_client_hello`, `tls_handshake`, and `http`. Each observer writes a
raw output artifact before JSON parsing. Execution, parsing, and persistence
failures produce a canonical `EXECUTION_FAILED`, `MALFORMED`, or `MISSING`
artifact with a terminal error classification. Aggregation runs only after both
observer artifacts are present and valid; aggregation errors return
`DIAGNOSTIC_INCOMPLETE` without mutating either input artifact.

The PowerShell controller validates schema version, observer identity, exact
phase keys, exact summary keys, artifact status, and execution identity. The
Python artifact module validates the same contract and rejects unknown or
case-variant fields. Readiness uses bounded 2/4/8/16/32-second backoff and
records provider state, timestamps, retry count, and both summaries per attempt.

## Local fault-injection evidence

`scripts/r4_vke_connectivity_artifacts_test.py` covers malformed Operator and
Tokyo artifacts, Operator and Tokyo execution failures, aggregation exceptions,
one-side missing artifacts, and the Operator-path differential classification.
The controller tests assert raw-first persistence, independent wrappers,
failure artifact construction, strict schema checks, and all required phases.
No mock result is presented as external evidence.

## Resource, security, and cost boundary

The v3 contract preserves exactly one minimal HA VKE with one worker, one Tokyo
observer, one recovery firewall, one SSH `/32`, and two VKE API TCP 6443 `/32`
rules. It creates no RouteMind or SigNoz workload, PVC, Block Storage, Load
Balancer, or public application ingress. Maximum runtime is two hours and the
incremental ceiling is USD 5.00. Prior conservative spend is USD 8.80 and the
aggregate ceiling remains USD 15.00. Secrets remain environment-injected and
outside Git, evidence, logs, fixtures, screenshots, and tracked `.env` files.

No Vultr resource was created, modified, or deleted during v3 preparation. The
contract's teardown requires exact identity-scoped destroy, four provider
`404` checks, zero execution-label inventory, and deletion of kubeconfig/state
and private-key material.

## Gate and disposition

All targeted Python tests, controller tests, plan tests, offline preflight,
security gate, and repository controls pass locally. v3 is prepared but not
approved for paid execution. The next human action is to approve the exact
contract digest above at `VKE CONNECTIVITY DIAGNOSTIC V3 HUMAN GATE`, including
the two-hour/USD 5 boundary and mandatory teardown. R4-405 and R4-406 remain
`TARGET_PENDING`; R3-325 remains exactly
`E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`.
