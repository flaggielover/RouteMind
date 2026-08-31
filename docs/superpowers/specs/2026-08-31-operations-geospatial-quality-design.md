# RouteMind Operations Geospatial Quality Design

## Objective

Raise the existing RM-244 three-city Operations world from a functional real-map
prototype to a credible operational geospatial interface. Preserve the React 19
application, seven chapters, one persistent MapLibre/Deck canvas, city switching,
deterministic Demo provenance, accessibility, reduced motion, and existing business
contracts.

This checkpoint is RM-245 and depends on RM-244. It does not reopen or rewrite the
already-passed RM-244 evidence.

## Chosen approach

Use deterministic, city-specific road-corridor geometry owned by the frontend Demo
adapter. Do not call a public routing provider at runtime and do not ship a browser
road-graph router. The geometry will be visibly street-like and tied to recognizable
city morphology, but remains explicitly synthetic rather than historical rider GPS.

The alternatives were rejected for this checkpoint:

- Runtime public routing would improve path fidelity but add availability, privacy,
  quota, and provider-qualification dependencies.
- Client-side OpenStreetMap graph routing would preserve offline behavior but add a
  large data and compute surface disproportionate to a visual correction pass.

## Data contract

`cityGeo` retains the public city, trajectory, node, hotspot, risk-zone, and flow
contract. Its generator changes from free-space Bezier curves and rectangular zones
to the following deterministic structures:

- road-corridor polylines with explicit merchant, pickup, courier, and destination
  relationships;
- route headings derived from adjacent path points;
- compact hexagonal pressure/risk cells distributed around operational anchors;
- aggregate district flows that remain separate from individual courier routes;
- three distinct city patterns: Shanghai cross-river, Shenzhen east-west clusters,
  and Chengdu ring/radial circulation.

No generated coordinate is labeled as real telemetry. `DEMO / SIMULATED` remains
visible in the spatial world.

## Basemap and layer composition

The MapLibre style gains a restrained cartographic hierarchy: land use and parks,
clearly separated water, minor streets as texture, stronger secondary/primary road
casings and fills, rail context, subtle buildings, and selective place/road labels
when the vector source exposes the required fields.

Deck layers are composed semantically by chapter:

- Overview: thin aggregate district corridors, subdued individual paths, city-wide
  context.
- Pressure: spatial pressure cells and supply imbalance dominate at a closer pitch.
- Risk: risk cells, delayed routes, and risk corridors dominate.
- Strategy: balancing flows and repositioning structure dominate.
- Live: individual paths, riders, pickups, destinations, and selection dominate.
- Replay: path progression and fading temporal context dominate.
- Research: stable low-motion evidence geography with restrained overlays.

Individual paths use `PathLayer`; aggregate flows may use restrained `ArcLayer` only
at overview scale. Couriers use directional compact markers, while merchant and
customer nodes use distinct size/outline grammars. Risk uses low-profile hexagonal
cells rather than arbitrary polygons.

## Pointer inspection lens

Reuse the existing normalized pointer frame and controller. `setPointerFrame` will
be implemented in the persistent map controller and will update refs and CSS custom
properties without React state on every pointer frame.

One DOM lens overlay sits above the existing map canvas and below controls. It uses
local backdrop contrast, clarity, and bounded edge refraction; it does not create a
second WebGL renderer. Pointer velocity controls a short chromatic edge response,
which decays to zero at rest. Reduced motion disables chromatic/distortion motion but
retains static semantic focus.

Deck picking remains the semantic authority. Hovering a courier emphasizes its
route and endpoints; hovering a route emphasizes its rider relationship; hovering a
risk cell emphasizes the local risk value. Controls and HUD elements suppress the
lens.

## Lifecycle and performance

The existing lazy WebGL2 capability gate, DPR cap, visibility pause, load timeout,
fallback, MapLibre removal, Deck finalization, and animation cancellation remain.
Overview, Pressure, Risk, Strategy, and Research keep courier markers static after
their semantic frame resolves. Only Live and Replay advance courier positions, with
layer refreshes capped near 5.5 updates per second; the deliberately slow movement
keeps sub-frame displacement small while avoiding a full interleaved map redraw on
every browser frame. Pointer-lens position remains compositor-driven. City switching
uses the existing persistent map with restrained camera easing and no remount.

## Verification

Browser gates are mandatory and must cover Shanghai Overview, Pressure, Live,
selected courier, pointer movement/rest/leave, Shenzhen Overview, Chengdu Overview,
reduced motion, 1024x768, and 760x800. The result fails if routes still read as
airline arcs, risk reads as rectangles, the lens is effectively invisible, controls
are distorted, or the page has overflow or console errors.

Automated gates cover data determinism and geometry semantics, controller/component
behavior, format, lint, typecheck, unit tests, production build, focused Playwright,
full relevant browser smoke, repository verification, and production dependency
audit. Evidence is recorded under `evidence/gates/RM-245/` before the task can pass.

## Scope boundaries

This checkpoint does not add production route geometry, H3 infrastructure, live GPS,
new backend APIs, a routing provider qualification claim, a calibrated Digital Twin,
or another page-level visual redesign.
