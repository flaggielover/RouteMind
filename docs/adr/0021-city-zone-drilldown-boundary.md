# ADR-0021: City and Zone Drilldown Projection Boundary

Date: 2026-08-24
Status: Accepted

## Context

The multi-city surface establishes coordinate-backed city aggregation, but
operators also need a closer view of local demand and supply. The drilldown
must remain useful when a provider is stale or empty without turning a
client-side grouping into a new durable operational record.

## Decision

Add a Web-owned city/zone drilldown projection over the selected
`OperationsSnapshot`. At city zoom it aggregates a city row; at zone zoom it
groups snapshot orders, merchants, courier supply, route counts, density, and
risk by the existing zone labels. The projection declares the source label
(`LIVE`, `DEMO`, `REPLAY`, or `SIMULATION`) and freshness state (`fresh`,
`stale`, `empty`, or `unavailable`). All metrics include visible units and a
legend. Schematic route bucketing is explicitly descriptive and never mutates
Java durable order state.

The panel is read-only and uses the existing provider-neutral snapshot
boundary. It renders a truthful empty/unavailable state and keeps stale
metrics inspectable while labeling them stale. The zoom control is bounded to
the supported city/zone range and the table's overflow region is keyboard
focusable for mobile and assistive technology users.

## Consequences

Operators can compare local demand, supply, and risk with clear data lineage
without implying that demo or replay points are live dispatch authority.
Future providers can populate the same projection contract while preserving
freshness and source semantics. A later map layer may replace the descriptive
route bucketing only when it carries analytical lineage and evidence.
