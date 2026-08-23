# RM-222 Multi-City Geo Operations Evidence

Date: 2026-08-24
Implementation checkpoint: 1a6f2fb
GitHub Actions: PASS - run 32654207318 (all five jobs)

## Scope

The Web Operations surface now includes a multi-city geo projection panel. It
uses explicit `DEMO data` fixtures with coordinate-backed city signals for
volume, supply, risk, and strategy, plus a stable projection digest. National,
multi-city, and city-detail tabs expose their scope and aggregation behavior.

National scope uses zoom 4 and `city-centroid` aggregation; multi-city uses
zoom 6 and the same aggregation. Both hide raw operational points. City detail
uses zoom 11 and declares `operational-point` semantics. The UI states these
boundaries directly and does not imply nationwide production operation.

## Local evidence

- `npm run check` in `apps/web` - PASS, 57 unit tests, Prettier, ESLint,
  TypeScript, and production build.
- `./scripts/web.ps1 e2e` - PASS, 34 browser tests with 2 existing desktop-only
  skips across desktop/mobile role routes and accessibility smoke.
- `src/domain/multiCityGeo.test.ts` - PASS projection aggregation, source and
  zoom semantics, raw-point boundary, WGS84/metric validation, and duplicate
  identity rejection.
- `src/components/MultiCityGeoPanel.test.tsx` - PASS DEMO labeling, national
  raw-point hiding, scope switching, and city-detail semantics.
- `./scripts/full-gate.ps1` - PASS, including Java 80 tests, Compute 208 tests
  at 95.29%, Web 57 unit tests/build, contracts, and repository gates.

## Boundary and limitations

The demo city signals are not live national operations data. The projection is
read-only and does not mutate Java order state. City-centroid aggregation is a
viewport rule, not a spatial accuracy claim; future live or replay providers
must preserve the source label and coordinate lineage.

## Remote validation

GitHub Actions run `32654207318` passed the Java, control-plane/Compose,
Python/contracts, Web static/unit/browser, and bounded degradation/resilience
jobs for checkpoint `1a6f2fb`.
