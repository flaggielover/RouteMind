# RM-111 Provider-Neutral Geospatial Map Adapter

- Date: 2026-08-22 (Asia/Shanghai)
- Revision: `d73be4f`; Actions run `32567620315`
- Boundary: Web geospatial contract and deterministic local fallback

## Adapter behavior

The Web domain now defines validated WGS84 coordinates, map bounds, markers,
routes, zones, selection, and provider capability status. `GeospatialMapAdapter`
returns a typed projection with center, zoom, freshness, and explicit
provider mode. The local schematic adapter maps bounded x/y fixture coordinates
into a declared geographic envelope and reports that tiles and routing are not
configured; it does not require a paid credential or network service. The existing
operations map labels this projection as a local schematic fallback.

## Executable evidence

1. `npm run check` in `apps/web` -> PASS; formatting, ESLint, TypeScript, 21 unit
   tests, and production build.
2. `npm run test:e2e` in `apps/web` -> PASS; 16 desktop/mobile role, viewport,
   and axe accessibility tests.
3. `./scripts/full-gate.ps1` -> PASS; Java 57 tests, Python 59 tests at 96.13%
   coverage, 5 schemas/15 fixtures, and Web static/unit/build gate.
4. `git diff --check` -> PASS before checkpoint commit.

## Evidence limits

This gate proves the provider-neutral contract and deterministic local fallback.
It does not claim external tile availability, provider-backed routing, map
attribution, or production-scale geographic rendering; those are RM-112 scope.
