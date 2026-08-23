# ADR-0022: Data-Backed Flow Visualization Boundary

Date: 2026-08-24
Status: Accepted

## Context

The city/zone drilldown exposes local aggregates, but operators also need to
see how order demand moves between areas. A curved line with no lineage would
be decorative and could be mistaken for a live routing decision.

## Decision

Add a Web-owned flow projection over `OperationsSnapshot.orders` whose route
arrays are the analytical source records. Each route-bearing order contributes
its first and last coordinate, is assigned to the nearest snapshot courier
zone anchor (or a clearly labeled normalized fallback area), and is
aggregated by source/target area pair. The projection declares:

- volume as an order count;
- direction from the aggregate endpoint vector;
- recency as minutes since the snapshot timestamp;
- confidence as a bounded 0-100% geometry and zone-lineage score; and
- evidence as the contributing order IDs.

The Operations UI renders these records as a bounded SVG projection and an
accessible selectable list. Selecting a flow reveals its metrics and order
evidence. Fresh, stale, empty, and unavailable source states are explicit;
route-less orders render no arcs. The projection is read-only and does not
create or mutate Java durable dispatch state.

## Consequences

Operators can inspect directional demand while preserving metric units,
freshness, and evidence lineage. Future analytical providers can replace the
route-record adapter without changing the UI contract. Production routing
authority remains in the Java lifecycle and dispatch boundaries; this panel
is explanatory analytics only.
