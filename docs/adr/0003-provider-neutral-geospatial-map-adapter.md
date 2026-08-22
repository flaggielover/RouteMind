# ADR 0003: Provider-Neutral Geospatial Map Adapter

- Status: Accepted
- Date: 2026-08-22

## Context

The operations surface needs geographic coordinates, markers, routes, zones, and
selection without making a paid tile or routing provider a prerequisite for local
development. The existing schematic map is useful as a deterministic projection,
but its x/y coordinates cannot be treated as geographic truth or as a provider
contract.

## Decision

The Web domain exposes a provider-neutral `GeospatialMapAdapter` contract. Its
projection carries WGS84 coordinates, bounds, center/zoom, markers, routes, zones,
selection, generated time, and explicit tile/routing capability status. A local
schematic adapter is the deterministic fallback; it maps bounded percentage
coordinates into a declared local geographic envelope and reports
`local-fallback`, `not_configured`, and no attribution requirement.

The adapter owns projection and selection semantics. React owns presentation and
interaction only. A real provider may be added behind the same contract when tile,
routing, scaling, ownership, and credential requirements justify it. Provider
availability must remain explicit and must not silently turn the local fallback
into live geographic truth.

## Consequences

- Local tests need no paid credentials, network tiles, or large road graph.
- RM-112 can add a real map layer without changing operations domain consumers.
- The current x/y fixture remains useful but is explicitly labeled schematic.
- Route geometry, provider attribution, and network failures remain follow-on
  capabilities and cannot be claimed by this contract alone.
