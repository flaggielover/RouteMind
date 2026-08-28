# ADR-0038: Retire HERE and activate the Google replacement boundary

Date: 2026-08-28  
Status: Accepted

## Context

HERE support ticket `CS0184597` confirmed that Japan access for HERE Matrix
Routing API v8 must proceed through a commercial entitlement/sales process.
RouteMind will not pursue that process. Earlier HERE contracts, diagnostics,
cost records, and failure evidence are frozen historical evidence and contain no
claim of live validation or production readiness.

## Decision

HERE is retired from active RouteMind runtime, configuration, deployment, and
product selection. The provider-neutral travel interface now selects
`GoogleRoutesProvider` as the primary external adapter and
`LocalRoutingProvider` (`deterministic-local`) as an explicit fail-closed,
provenance-carrying fallback. The runtime default transport is intentionally
unconfigured, so local tests and ordinary startup cannot make a Google live
call. Google Routes live validation remains independently gated by R4-411B and
its frozen contract digest.

The historical HERE contract files, evidence, ADRs, and frozen-contract
validators are retained, labeled historical, and are not active credentials or
runtime dependencies.

## Consequences

The active secret boundary is `ROUTEMIND_GOOGLE_ROUTES_API_KEY`, checked only by
presence and injected externally. `ROUTEMIND_TRAVEL_PROVIDER_API_KEY` is no
longer an active requirement. Point and matrix Japan support are evaluated only
under the Google contract; no Matrix entitlement or live/production claim is
made before its Human Gate.
