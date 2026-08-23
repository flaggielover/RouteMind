# ADR-0028: Immutable Event Upcasting for Historical Replay

Date: 2026-08-24  
Status: Accepted

## Context

Historical events outlive the read models that first consumed them. Replay and
research surfaces need a bounded compatibility path without rewriting the
immutable archive or allowing an unknown schema to appear current.

## Decision

Compute owns a pure `EventUpcasterRegistry` and `HistoricalEvent` envelope. Each
event type declares one current integer schema version, and every transition is
registered as an additive one-step transform. The read-only
`POST /api/v1/replay/upcast` adapter parses archived events, applies the explicit
chain, and returns source/read-model digests plus the upcast path.

The original event identity, event time, clock domain, trace ID, reference-data
identity, and replay digest are copied unchanged. Unknown event types, newer
versions, missing transitions, malformed transforms, and invalid payloads fail
with structured compatibility codes. Java remains the owner of durable event
records and transactional publication; this adapter never mutates durable state.

## Consequences

- Historical replay remains deterministic and auditable across additive schema
  changes.
- A new event version requires an explicit transition and focused contract
  tests; silent fallback is impossible.
- Upcasting is a projection concern and does not create a second durable event
  store or alter dispatch correctness.
