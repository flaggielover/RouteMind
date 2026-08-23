# ADR-0024: Read-Only Decision X-Ray Boundary

## Context

RouteMind already persists the Java-owned dispatch decision ledger with bounded
input/output snapshots and content digests. Operators need to inspect why a
decision was selected without moving dispatch correctness into the browser or
turning incomplete snapshot fields into invented travel metrics.

## Decision

The business API exposes a read-only lookup at
GET /api/v1/dispatch-decisions/{decisionId}. The response is a projection of
the PostgreSQL ledger and preserves the decision identity, strategy/version,
reference-data identity, clock domain, bounded snapshots, and all four digests.
Missing records return 404; the endpoint does not mutate state.

The Web Decision X-Ray consumes structured snapshot data and uses the durable
ledger record when attached. When only an operations snapshot is available, it
labels itself snapshot-projection, derives only bounded candidate/status
signals, and marks reference data, travel, and ledger digests unavailable. The
summary is assembled from those structured fields and is not an independent
natural-language authority.

Bounded replay compares a canonical digest of captured decision inputs with a
replayed snapshot. It reports match, changed, or not-captured; replay never
mutates the Java ledger.

## Consequences

- Java remains the durable authority and Python remains the dispatch computation owner.
- Operators can inspect candidate rejection reasons, selected action, alternatives,
  objective/risk proxies, verification checks, and provenance in one surface.
- Travel values are not inferred from schematic positions. Provider travel records
  must be attached before a travel duration is shown.
- A future live client can attach a ledger record by decision ID without changing
  the X-Ray contract.
