# RM-245 Geospatial Quality and Pointer Lens Evidence

## Scope

- Base revision: `dc73709`
- Date: 2026-08-31
- Classification: `PRODUCT`, excluded from Round 4 counts
- Target: focused quality continuation of the passed RM-244 three-city map

OpenFreeMap/OpenMapTiles remains the geographic source. Courier paths, riders,
orders, pressure, flows, and risk are deterministic `DEMO / SIMULATED` fixtures.
This checkpoint does not claim historical GPS, production route geometry, H3,
provider qualification, or calibrated Digital Twin state.

## Implemented quality pass

- Expanded the MapLibre style into a restrained road hierarchy with minor,
  secondary, and primary casings/fills, water and waterway separation, rail,
  land-use, buildings, and selective labels.
- Replaced free-space Bezier rider routes with deterministic multi-segment road
  corridors. Shanghai crosses the Huangpu and distinguishes Puxi/Pudong, Shenzhen
  uses elongated east-west clusters, and Chengdu uses ring/radial circulation.
- Added chapter-specific level of detail: Overview favors thin aggregate flows;
  Pressure and Risk emphasize low-profile spatial cells; Strategy favors balancing
  flows; Live exposes individual paths and agents; Replay advances movement; and
  Research stabilizes the evidence view.
- Replaced rectangular risk overlays with ten compact hexagonal cells per city.
  Courier, merchant, destination, risk, hotspot, aggregate-flow, and selected-route
  grammars are distinct by shape, size, line treatment, label, and color.
- Restored a rounded-square local inspection lens using the existing map/controller
  and normalized pointer frame. It updates CSS variables through refs, does not add
  a canvas or React state per pointer frame, suspends over controls/HUD, and reduces
  transient chromatic response to zero at rest.
- Semantic Deck picking highlights the related route and pickup/destination nodes,
  exposes lightweight metadata, and supports selected-courier inspection.
- Disabled MapLibre wheel zoom so the sticky spatial world cannot trap the page's
  seven-chapter scroll narrative.

## Browser visual gate

The current workspace was reviewed repeatedly in the real in-app browser at
`http://127.0.0.1:4175/operations`, not only in automated Playwright.

- Shanghai Overview: Huangpu, arterial hierarchy, urban blocks, aggregate flows,
  and asymmetric world/page composition are legible without giant tubes.
- Shanghai Pressure: closer pitched geography and distributed cells lead while
  the city and road network remain readable.
- Shanghai Live: individual multi-turn paths, heading markers, pickup/destination
  glyphs, route metadata, and selected courier `SH-C13` are inspectable.
- Shenzhen and Chengdu: switching preserves chapter state and produces visibly
  different east-west and ring/radial morphologies; selection clears correctly.
- Lens: active map state reached `0.92` opacity with a 166 px local region; pointer
  motion produced a transient response and the recorded rest state returned
  `--geo-lens-motion` to `0.000`. Controls remain undistorted.
- Reduced motion: the real map, city, paths, risk, semantics, and static lens remain;
  flowing motion and chromatic displacement are disabled.
- Responsive: 1024x768 and 760x800 both reported document width equal to viewport
  width, with no horizontal overflow. The 760 layout moves the spatial world above
  chapter content without text collision.
- Continuous scroll over the map advanced through Pressure, Risk, Strategy, Live,
  Replay, and Research rather than zooming the map or remaining trapped at the top.
- A fresh browser pass contained one canvas, a ready map, and zero console errors or
  application warnings. External tile latency was allowed to resolve before the
  Chengdu visual judgment.

Representative evidence:

- `screenshots/01-shanghai-overview.png`
- `screenshots/02-pointer-lens.png`
- `screenshots/03-shanghai-pressure.png`
- `screenshots/04-shanghai-live.png`
- `screenshots/05-shenzhen-overview.png`
- `screenshots/06-chengdu-overview.png`
- `screenshots/07-reduced-motion.png`
- `screenshots/08-laptop.png`
- `screenshots/09-mobile.png`
- `screenshots/10-selected-courier.png`

Visual verdict: **PASS**. The result reads as a city courier network rather than a
dark map with airline arcs, arbitrary rectangles, or airport endpoints.

## Performance gate

The first headed-Chrome sample exposed a real issue: updating all interleaved Deck
layers about 15 times per second reduced the idle Overview sample to roughly 26-31
frames per second. That result was treated as a failed implementation gate.

The fix freezes agents in non-temporal chapters and limits full Deck position
updates to Live and Replay at about 5.5 Hz. Headed-Chrome samples after the fix:

- Overview: 4.83 ms mean frame interval, 7.70 ms p95, 0 frames over 25 ms in 180
  samples. The browser was uncapped, so the derived ~207 FPS is capacity headroom,
  not a monitor-refresh claim.
- Live: 16.13 ms mean, 34.90 ms p95, derived ~61.98 FPS while riders advance.
- Synthetic worst-case continuous pointer dispatch over Live: 24.22 ms mean,
  54.20 ms p95, derived ~41.30 FPS while lens work and semantic picking compete.
- Reduced motion: no continuous Deck layer update; the full real basemap remains.

Actual in-app-browser pointer, city switching, and continuous scroll inspection had
no visible input lag or blank frame. These are local workstation measurements, not
a production hardware benchmark or SLA.

## Automated verification

- `npm run check`: PASS; Prettier, ESLint, TypeScript, 43 Vitest files / 119 tests,
  and Vite production build.
- Focused geometry/component tests: PASS; 2 files / 6 tests.
- `npx playwright test --reporter=line`: PASS; 37 passed / 3 intentional
  device-conditional skips.
- `npm audit --omit=dev`: PASS; 0 vulnerabilities.
- `./scripts/verify.ps1`: PASS; task graph, repository integrity, security, research,
  control-plane, contract, Compose, and fast repository gates.

The Vite build retains the existing warning that the lazy map bundle exceeds 500 kB;
the map remains route-lazy and this checkpoint adds no eager load to other product
surfaces.

## Boundaries

No backend ownership changed. Java remains durable business authority and Python
retains optimization/simulation ownership. No external route provider, paid API,
production telemetry, cloud mutation, H3 service, or scientific claim was added.
