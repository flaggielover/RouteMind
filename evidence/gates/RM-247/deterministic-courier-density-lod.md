# RM-247 Deterministic Courier Density + LOD Evidence

Date: 2026-08-31  
Classification: Product / deterministic Demo visualization  
Production telemetry: not used  
Checkpoint status: local visual gate passed

## Contract

The real OpenFreeMap/OpenMapTiles basemap remains the geographic context. Courier
positions, velocities, risk values, route variants, and handoff relationships are
synthetically generated from stable per-city seeds. The rendered source is labeled
`DEMO / SYNTHETIC`; no live courier telemetry, H3 feed, calibrated Digital Twin,
or production claim is introduced.

| City | Synthetic couriers | Emphasized trajectories | District routes |
| --- | ---: | ---: | ---: |
| Shanghai | 120 | 32 | 16 |
| Shenzhen | 90 | 26 | 12 |
| Chengdu | 104 | 28 | 14 |

## Browser Gate

The local page was inspected at `http://127.0.0.1:4175/operations` in the real
browser after the production build was refreshed.

- Shanghai overview: HUD reported `120` couriers, `32` focus routes, `CITY` LOD.
- Shenzhen overview: HUD reported `90` couriers, `26` focus routes, `CITY` LOD.
- Chengdu overview: HUD reported `104` couriers, `28` focus routes, `CITY` LOD.
- Chengdu Urban Pressure focus: HUD reported `48` visible context couriers and
  `14` visible routes under `DISTRICT` LOD.
- Chengdu selected courier: HUD reported `22` visible context couriers and `5`
  routes under `SELECTED` LOD. The selected panel retained courier, order, ETA,
  SLA risk, strategy, and `merchant -> customer` handoff semantics.
- Overview retains aggregate flows and a dense but quiet population field; focused
  and selected states remove unrelated paths instead of reducing the underlying
  synthetic population.
- The smaller square optical lens remains visible over the map, with native cursor,
  map-only activation, and existing motion-sensitive RGB behavior intact.

Screenshots: `01-shanghai-overview.png`, `02-shenzhen-overview.png`,
`03-chengdu-overview.png`, `04-chengdu-district.png`, and
`05-chengdu-selected.png`.

## Automated Evidence

- `cityGeo.test.ts`: deterministic equality, exact city populations and route
  counts, WGS84 bounds, route/agent endpoint relationships, city/district/selected
  LOD membership, and city switching.
- `PersistentGeoWorld.test.tsx`: single map/lens lifecycle, truthful density HUD,
  and city control behavior.
- `mapOpticalLens.test.ts`: reduced lens sizing from the approved `0.29` short-edge
  ratio with a `170-240 px` clamp, plus unchanged distortion/RGB contracts.
- Local Web check: 44 Vitest files / 124 tests, typecheck, lint, format, and build
  passed. The existing Vite large-chunk advisory remains non-blocking.
- Focused Playwright real-map gate: desktop passed; mobile remains the existing
  device-conditional skip for this real-map WebGL scenario.

## Intentional Differences

This is not production telemetry and does not claim city-scale operational truth.
The full population is represented by small unlabelled agents, while semantic
routes are a bounded emphasized subset. This preserves the Codrops optical lens and
the RouteMind operational scene without turning a city overview into spaghetti.
