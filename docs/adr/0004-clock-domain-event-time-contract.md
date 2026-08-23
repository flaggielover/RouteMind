# ADR 0004: Explicit Clock Domains and Event-Time Semantics

Status: Accepted  
Date: 2026-08-23

## Decision

RouteMind uses three explicit clock domains at product and compute boundaries:

- `WALL` is UTC wall time owned by the Java business runtime and used for live
  durable records, event `occurredAt`, ingestion-independent freshness, and live
  API `generated_at` values. Java obtains it through the injected UTC `Clock`.
- `SIMULATED` is the Python Digital Twin tick/second timeline. It advances only
  from commands or scenario events and never reads wall time. Scenario digests
  include the domain, so a simulation cannot be mistaken for a live event.
- `REPLAY` is the verified artifact timeline in the Web replay boundary. Cursor
  movement and visible event selection use artifact seconds only; verification
  and UI ingestion may still produce a separate wall-time `generatedAt` value.

The existing event contract remains version `1.0`. Its `occurredAt` field keeps
its meaning as producer event time in the producer's declared domain. Transport
or consumer receipt time is ingestion time and is not substituted into
`occurredAt`. Existing consumers remain compatible because the new clock-domain
fields are additive response/provenance metadata; old payloads may be read with
the historical default (`WALL` for live and `SIMULATED` for Twin responses).

## Consequences

Replay and simulation tests can run repeatedly without wall-clock dependence,
while live snapshots still expose UTC wall-time freshness. Operational command
identifiers no longer need wall-clock entropy in simulation/replay UI paths.
Future event consumers must preserve both event time and receipt time when they
need latency or freshness analysis; they must not rewrite the durable event
timestamp.
