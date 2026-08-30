# RM-244 Multi-City Real Map Evidence

## Scope

- Base revision: `46a5568`
- Date: 2026-08-31
- Classification: `PRODUCT`, excluded from Round 4 counts
- Target: replace the abstract Operations world with one persistent real-city
  geographic map for Shanghai, Shenzhen, and Chengdu

OpenFreeMap/OpenMapTiles supplies geographic context only. Courier trajectories,
orders, hotspots, flows, and risk zones are deterministic `DEMO / SIMULATED`
fixtures. This checkpoint does not claim production rider telemetry, calibrated
Digital Twin state, provider qualification, or backend ownership changes.

## Implemented system

- Replaced the persistent Three.js mount with one lazy MapLibre GL JS 5.24 map
  and an interleaved Deck.gl 9.3 operational overlay. Routes, moving couriers,
  pickups, destinations, hotspots, aggregate flows, and SLA-risk polygons share
  the map's WebGL context.
- Added a RouteMind vector style over the OpenFreeMap OpenMapTiles source. It
  keeps graphite land, water, roads, boundaries, and restrained building
  extrusion without remote glyph dependencies. Required attribution remains
  visible.
- Added deterministic, city-specific datasets and semantic picking for
  Shanghai, Shenzhen, and Chengdu. City switching preserves the active chapter
  and clears a trajectory selection that is invalid in the new city.
- Preserved seven chapter roles. Overview, Pressure, Risk, Strategy, Live,
  Replay, and Research change center, zoom, pitch, bearing, route emphasis,
  aggregation, risk, and instrumentation around the same persistent map.
- Added a renderer-neutral controller boundary, a pre-import WebGL2 capability
  gate, DPR cap `1.5`, visibility-aware animation, reduced-motion freeze,
  deterministic static fallback, load timeout, animation cancellation,
  Deck overlay finalization, and MapLibre disposal.
- Kept order selection, decision details, filters, and city selection keyboard
  reachable. The map host owns the accessible description; its raw renderer
  container does not carry prohibited ARIA attributes.

## Browser visual gates

The in-app browser inspected `http://127.0.0.1:4174/operations` against the real
local React application with Demo selected.

- `1280x720`: map status `ready`; one canvas; seven chapters; no legacy
  `.operations-map`; `scrollWidth=1265` for `innerWidth=1280`; Shanghai overview
  showed real streets/water/buildings, ten courier trajectories, bounded risk
  zones, city controls, provenance, map legend, and narrative typography in one
  composition.
- `1024x768`: `scrollWidth=1009` for `innerWidth=1024`; the map and narrative
  remain side-by-side without horizontal overflow. Chengdu preserved the active
  city and returned from Research to Overview through normal scrolling.
- `760x800`: `scrollWidth=745` for `innerWidth=760`; the persistent map becomes a
  full-width `745x416` first visual field and leaves the Overview chapter visibly
  entering below it. City controls, legend, provenance, and inspection copy fit.
- Multi-city: Shanghai, Shenzhen, and Chengdu each reached map status `ready`.
  Switching Shanghai to Shenzhen at Research preserved `world=research`, kept
  the scroll position, and cleared the selected trajectory. Chengdu preserved
  the same chapter before the next scroll hand-off.
- Semantic pointer: hovering a visible Shanghai risk surface produced
  `Jing'an merchant SLA zone · SLA risk region`, confirming local inspection
  rather than a decorative distortion.
- Continuous scroll: browser wheel input traversed the whole page, producing
  `overview -> pressure -> risk -> strategy -> live -> replay -> research`.
  Camera/world role hand-offs occurred across the same map; Live Operations
  remained the intentionally densest chapter while Replay and Research regained
  wider spatial context.
- Reduced motion: WebGL remained available with `data-motion-reduced=true`, map
  status `ready`, one canvas, and no fallback; route movement and nonessential
  camera animation were frozen.
- Capability fallback: an invalid map style produced map status `fallback` with
  all three city buttons, a deterministic static city field, route/rider/risk
  semantics, and the `SIMULATED` provenance marker still visible.
- Final browser console warnings/errors: `0`.

The rendered result was reviewed as a continuous operational environment, not
as isolated screenshots. The persistent geographic world, asymmetric chapter
layouts, analytical surfaces, HUD, and typography remain visually integrated;
the page does not revert to the removed dashboard-with-map-widget composition.

## Automated gates

- `npm audit --omit=dev`: PASS, zero vulnerabilities.
- `./scripts/verify.ps1`: PASS, including task graph, repository integrity,
  secret isolation, dependency metadata, and fast repository gate.
- `npm run check`: PASS.
  - explicit Prettier source/config scope
  - ESLint
  - TypeScript
  - Vitest: 43 files, 118 tests
  - Vite production build
- `npx playwright test --reporter=line`: PASS, 36 passed and 2
  device-conditional skips across desktop/mobile, including Axe accessibility.
- The mocked SSE reconnect test now verifies the durable protocol result after a
  closed response: the next request resumes from `after=2`, the UI truthfully
  reports reconnecting, and exactly two non-duplicate events remain.
- Production output keeps MapLibre/Deck in a lazy
  `PersistentGeoWorld` chunk. Vite's existing 500 kB advisory remains explicit;
  the main application does not synchronously import the map engine.

## Result

RM-244 passes its local product and visual gates. RouteMind Operations now uses
one real three-city geographic world with synthetic courier operations, semantic
inspection, seven chapter recompositions, accessible controls, bounded motion,
and deterministic capability failure behavior.
