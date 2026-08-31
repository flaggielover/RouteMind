# RM-249 Full-detail MapLibre basemap

Date: 2026-08-31

Result: **PASSED / LOCAL VISUAL CHECKPOINT**

## Scope and audit

Operations continues to use MapLibre GL JS as the basemap renderer and Deck.gl as
the provider-independent operational layer. No Google Maps SDK, API credential,
billing dependency, production telemetry, or production route claim was added.

The prior normal desktop style used the real OpenFreeMap planet vector source,
but exposed only 16 handwritten layers. A second broad type-based transform then
collapsed most fills, lines, and symbols into a few dark colors. The geographic
data was materially richer than the presentation: roads lost class hierarchy,
land use and water context disappeared, labels were flattened, and all three
cities read as coarse diagrams.

RM-249 now loads the complete OpenFreeMap Liberty style from
`https://tiles.openfreemap.org/styles/liberty`. The runtime style exposes 111
layers. A semantic RouteMind graphite transform changes 277 supported paint
properties while preserving source filters, zoom ranges, widths, layer order,
label fields, and collision behavior. The resulting style retains separate
motorway, primary, secondary, minor, service, bridge, tunnel, rail, water,
land-use, building, boundary, district, place, road-label, water-label, and
selective POI treatment.

## Provider and attribution

- Provider: OpenFreeMap Liberty.
- Geography: OpenStreetMap-derived vector data in the OpenMapTiles schema.
- Credentials: none for the selected public provider.
- Attribution: the source attribution remains rendered by MapLibre; RouteMind's
  custom attribution identifies the Demo operational overlay separately.
- Licensing: OpenFreeMap publishes the project/style under MIT and requires
  visible OpenStreetMap/OpenMapTiles attribution for the rendered basemap.
- Operational risk: the public OpenFreeMap endpoint has no application SLA.
  Parallel browser teardown produced intermittent remote glyph-range warnings;
  MapLibre rendered labels locally and all browser gates passed. A production
  deployment should select a provider or self-hosting tier with an explicit
  availability and cache policy.

`basemapProvider.ts` owns provider identity, style URL, attribution, credential
status, quality tier, and theme policy. An explicit `VITE_MAP_STYLE_URL` is treated
as a configured provider and keeps its own style and attribution. Operational
Deck.gl data and layer construction remain separate, preserving a future Google
comparison/host adapter without coupling RouteMind semantics to Google.

## Routing independence

Road-following courier geometry is independent of the visual basemap. The Python
travel contract already supports optional `TravelTime.route_geometry`, and the
network provider can return deterministic shortest-path geometry. The current
Web Demo does not consume that geometry, while the current Google Routes adapter
requests distance and duration without a polyline. RM-249 therefore retains the
existing deterministic synthetic corridors and labels them `DEMO / SYNTHETIC`.

## Browser visual evidence

The in-app browser loaded `http://127.0.0.1:4175/operations` with one persistent
MapLibre/Deck.gl canvas. Runtime inspection reported:

- map status: `ready`;
- basemap provider: `openfreemap-liberty`;
- quality tier: `full-vector`;
- style layers: `111`;
- RouteMind theme mutations: `277`;
- optical lens mode: `webgl-cc-lens`.

Visual inspection covered all three city overviews. Shanghai retained its river,
crossings, rings, and dense street morphology; Shenzhen retained coastline,
mountain/green context, and its east-west urban corridor; Chengdu retained its
ring/radial network and district texture. Operational counts remained exactly:

- Shanghai: 120 synthetic couriers / 32 emphasized trajectories;
- Shenzhen: 90 / 26;
- Chengdu: 104 / 28.

Chengdu district focus reported 48 visible contextual couriers and 14 routes.
Live retained the compact Codrops-style optical square lens and Research retained
the persistent geographic world. A continuous 34-step scroll from the top to the
bottom observed all seven chapters in order (`overview`, `pressure`, `risk`,
`strategy`, `live`, `replay`, `research`), with map status continuously `ready`
and LOD transitions between `city` and `district`.

Captured evidence:

- `01-shanghai-overview.png`
- `02-shenzhen-overview.png`
- `03-chengdu-overview.png`
- `04-chengdu-pressure.png`
- `05-chengdu-live-lens.png`
- `06-chengdu-research.png`

The first browser pass was rejected because the complete style was too bright and
label-heavy. Road and label hierarchy was then retuned before the final captures.
Responsive and reduced-motion behavior were exercised by the full Playwright
device matrix; reduced motion keeps the WebGL map available and removes
nonessential transition motion.

## Automated gates

- Focused unit: 4 files / 17 tests passed.
- Full Web check: format, lint, typecheck, 45 Vitest files / 130 tests, and
  production build passed.
- Focused geographic Playwright: 2 passed.
- Full Playwright: 38 passed / 4 intentional device-conditional skips.
- Dependency audit: 0 production vulnerabilities.
- `git diff --check`: passed (line-ending notices only).

## Claim boundary

This checkpoint proves a higher-detail legitimate MapLibre-compatible basemap,
provider separation, preserved deterministic Option B visualization, and local
browser behavior. It does not prove live courier telemetry, production route
geometry, provider SLA, calibrated spatial state, H3, or Google Maps superiority.
