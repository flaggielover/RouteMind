# ADR 0034: Tenant-Safe Telemetry Export Boundary

- Status: Accepted
- Date: 2026-08-25
- Decision owner: RouteMind engineering
- Task: R4-405

## Context

RouteMind already creates provider-neutral OpenTelemetry spans at HTTP,
messaging, dispatch, travel, solver, and verification boundaries. Round 4 must
extend correlation through workers, simulation, and experiments, then export
traces and metrics without exposing durable tenant identity or allowing an
observability failure to change business truth.

R4-401 selected Vultr `nrt` (Tokyo, Japan) as the target and data-residency
region. No telemetry backend, credentialed collector, or production resource
has been supplied or verified. The design must therefore be deployable while
remaining explicit that target qualification is pending.

## Decision

Applications use W3C Trace Context and bounded batch export. Java derives a
telemetry-only tenant key as the first 24 hexadecimal characters of an
HMAC-SHA256 digest, prefixed by `rtk_`. The secret comes from
`ROUTEMIND_TELEMETRY_ATTRIBUTION_KEY` in a deployed environment and must not be
committed. Raw tenant IDs remain valid durable business identifiers inside the
Java authority boundary, but are never metric labels or exported tenant trace
attributes.

Only the pseudonymous `X-RouteMind-Tenant-Key` may cross from Java to Python,
and only on a private authenticated service boundary. Python never computes a
tenant key from raw identity and treats malformed or absent keys as
`rtk_unattributed`. Each runtime admits at most 64 active tenant keys; later
keys use `rtk_overflow`. Request, trace, event, order, courier, principal, URL,
and exception-message values are forbidden metric dimensions. The planning
ceiling is 2,048 metric series per runtime.

Logical trace and metric records are counted by service, signal, operation, and
tenant key. This supports volume attribution only. Currency cost remains
unqualified until a selected target backend supplies usage and rate evidence.

The collector has memory limiting, raw-identity scrubbing, batching, a bounded
persistent sending queue, and bounded retry. Its endpoint and authorization
come only from environment variables. The application exporter is disabled by
default and has a 2,048-record queue, 512-record batches, five-second scheduling,
and a ten-second export timeout.

Telemetry is non-authoritative. Queue overflow, exporter failure, collector
outage, or retry exhaustion may lose telemetry and emit diagnostics; none may
block a business request, change a PostgreSQL transaction, acknowledge a
message, or trigger a business retry. PostgreSQL remains durable truth, the
Outbox remains event-production truth, and consumer acknowledgment remains
owned by business processing.

## Consequences

- Correlation covers HTTP, messaging, workers, simulation, and experiments.
- Tenant-level volume can be reconciled without exporting raw tenant identity.
- Pseudonym stability depends on protecting and consistently provisioning the
  attribution secret; rotating it starts a new attribution epoch.
- The runtime key limit bounds metric growth but intentionally groups excess
  tenants under `rtk_overflow`.
- Persistent collector buffering improves recovery but is still bounded and is
  not a business durability mechanism.
- R4-405 cannot pass from local contract tests or GitHub-hosted CI alone. It
  requires credentialed Vultr Tokyo identity, five-boundary trace continuity,
  a leakage scan, saturation observations, an outage/recovery drill, and backend
  usage/cost reconciliation.
- R3-325 remains exactly
  `E-PASS / X-PASS / S-FAIL / C-NO-CLAIM`; telemetry evidence is not scientific
  evidence and cannot promote a scientific claim.

The executable contract is
`contracts/observability/r4-405-telemetry-export-v1.json`; the candidate
collector configuration is `infra/observability/otel-collector.yaml`.
