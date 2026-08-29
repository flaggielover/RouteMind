# R4-422 local SES runtime dependency repair

Date: 2026-08-29

## Frozen boundary

The consumed single-send contract and its historical outcome remain immutable:

- Contract: `contracts/provider/r4-422-aws-ses-single-send-validation-v1.json`
- SHA-256: `e942a04b080da7cf42645d757fec61a1fb67428b59da29f90c93227b06c7d660`
- Historical result: `FAIL_LOCAL_RUNTIME_DEPENDENCY_BEFORE_SEND`
- AWS network requests, SendEmail requests, emails, and cost: `0`, `0`, `0`, and `USD 0.00`

No new live-send contract was created or executed by this repair.

## Root cause

The failed attempt used a manually assembled JShell classpath. It omitted
`org.reactivestreams.Publisher`, supplied by
`org.reactivestreams:reactive-streams:1.0.4`, and SES client construction failed
with `java.lang.NoClassDefFoundError: org/reactivestreams/Publisher` before HTTP
transport or request serialization. The application Maven dependency graph
already includes this dependency transitively through the AWS SDK v2 modules;
the defect was in the diagnostic launcher classpath, not the production
dependency boundary.

The isolated second attempt also remained a local client/runtime failure and is
preserved unchanged. No external retry was performed.

## Repair

`scripts/business-api.ps1` now exposes an explicit `ses-offline` action. It:

1. validates only the approved non-secret profile/region names;
2. disables EC2 metadata lookup for the local test process;
3. invokes the repository Maven Wrapper with `-Dmaven.repo.local=.tools/m2`;
4. runs the focused construction test with the complete Maven test runtime;
5. reports only safe status counters and never sends a request.

No production dependency was added or changed. The provider-neutral notification
architecture, `DefaultCredentialsProvider`, and default-disabled SES adapter
remain unchanged.

## Verification

- Focused offline test: `R4_422SesClientConstructionTests`, 1 passed, 0 failed
- Full Java suite: 125 tests passed, 0 failures, 0 errors
- Execution-path parity: `scripts/business-api.ps1 -Action ses-offline` passed
- `DefaultCredentialsProvider` local resolution: `AVAILABLE`
- `SesClient` construction and close: `AVAILABLE`
- AWS network requests: `0`
- `SendEmail` requests: `0`
- External cost: `USD 0.00`
- AWS/IAM/provider mutations: `0`
- Fallback: not used
- Credentials and credential identifiers: not recorded

The aligned dependency graph is retained at
`evidence/gates/R4-422/aws-sdk-ses-dependency-tree-20260829.txt`. All AWS SDK
modules are `2.31.77`; `reactive-streams` is `1.0.4`; SLF4J is managed at
`2.0.18`; Apache and Netty HTTP implementations are runtime-scoped as supplied
by the existing SES dependency graph.

## Tooling note

The standalone host Python environment still lacks `jsonschema`. The repository
declares `jsonschema==4.26.0` in the compute API dev dependency group; this is a
separate developer-environment/tooling issue and is not part of the SES repair.

## State

R4-422 is `BLOCKED / LOCAL_RUNTIME_REPAIRED_AWAITING_NEW_CONTRACT`. A future
live send requires a new exact contract and a new Human Gate. This repair does
not establish AWS connectivity, provider acceptance, delivery, or production
readiness.
