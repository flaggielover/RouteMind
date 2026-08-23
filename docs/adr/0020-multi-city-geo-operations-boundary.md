# ADR-0020: Multi-City Geo Operations Aggregation Boundary

Date: 2026-08-24
Status: Accepted

## Context

The existing operations map is a provider-neutral city surface backed by
schematic or configured tile coordinates. Extending it to national and
multi-city views must not imply nationwide production coverage, leak raw points
at an unsuitable zoom, or turn demo fixtures into live operational truth.

## Decision

Add a Web-owned multi-city projection contract with coordinate-backed city
signals for order volume, supply, risk index, and strategy. Every projection
declares its source as `DEMO`, `SIMULATION`, `REPLAY`, or `BENCHMARK`. National
scope uses zoom 4 and city-centroid aggregation; multi-city scope uses zoom 6
and the same aggregation; city detail uses zoom 11 and may expose operational
points. National and multi-city views therefore never render raw points.

The Operations surface presents the demo multi-city panel with scope tabs,
totals, risk, source label, city coordinates, strategy, and a deterministic
projection digest. This is a read-only product surface; provider-neutral map
adapters and Java durable-state ownership remain unchanged.

## Consequences

Users can compare coordinate-backed city signals while seeing the data-source
and aggregation boundary directly. A future live provider can implement the
same contract without changing zoom semantics. The panel is not a national
production-control claim, and city aggregates do not replace order-level
detail in the city scope.
