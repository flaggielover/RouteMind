# RouteMind Operations Basemap Quality Design

## Objective

Raise the three-city Operations basemap from a heavily reduced dark OpenMapTiles
rendering to a detailed operational cartographic foundation without replacing
MapLibre, Deck.gl, the persistent world, deterministic Demo density, or the
Codrops-style optical lens.

This checkpoint is RM-249 and depends on RM-248. It does not introduce Google
Maps, a paid tile credential, production courier telemetry, or a production route
claim.

## Audit

The current primary source is the public OpenFreeMap planet vector source at
`https://tiles.openfreemap.org/planet`. OpenFreeMap derives its data from
OpenStreetMap and exposes the unmodified OpenMapTiles schema. The source is real
geography rather than the local schematic fallback.

The default RouteMind style is not the complete OpenFreeMap style. It is a
handwritten 16-layer `StyleSpecification` inside `PersistentGeoWorld`. The
official OpenFreeMap Liberty style currently contains 111 layers across land
cover, land use, roads, tunnels, bridges, rail, water, boundaries, buildings,
district/place labels, water labels, road labels, and selective POIs.

The current `applyOperationalStyle` then applies broad type-based overrides to
every loaded layer. Most fills collapse into three near-black colors, most lines
collapse into a small set of low-contrast colors, and all symbols receive the same
text treatment. This removes hierarchy even when a configured external style
contains richer information. At the city overview zooms, subdued minor roads and
the absence of district/water label layers make Shanghai, Shenzhen, and Chengdu
read as coarse diagrams instead of recognizable cities.

## Options Considered

### Complete OpenFreeMap Liberty style with selective RouteMind theming

Use `https://tiles.openfreemap.org/styles/liberty` as the normal desktop style.
Preserve the complete layer graph and apply a restrained graphite operational
theme only to known semantic layer families. This requires no key and keeps the
existing source, renderer, Deck.gl interleaving, and lens pipeline. OpenFreeMap
permits commercial use and publishes its project/style under MIT; visible
OpenStreetMap and OpenMapTiles attribution remains required. The public service
does not provide an SLA.

### MapTiler Cloud

MapTiler provides curated MapLibre-compatible vector styles and additional source
data in some layers. It requires an API key, provider terms/quota management, and
visible MapTiler plus OpenStreetMap attribution. It remains a valid future provider
but is not justified solely to repair a destructive local style transform.

### Regional Protomaps PMTiles

Protomaps can provide self-hosted regional vector archives with deterministic
availability and full styling control. Its OSM-derived basemap is distributed as
an ODbL Produced Work and requires OpenStreetMap attribution. This path requires a
regional extraction, hosting, update, and integrity lifecycle and therefore belongs
to a later provider-hardening checkpoint.

## Decision

Use the complete OpenFreeMap Liberty style as the primary MapLibre basemap and
replace global type-based restyling with an explicit semantic theme transform.
The transform preserves upstream filters, zoom ranges, line widths, dash patterns,
label fields, collision behavior, and layer order. It changes only the visual
properties needed to integrate the map with RouteMind:

- graphite land and residential texture remain distinguishable;
- parks, woodland, grass, wetland, sand, hospitals, schools, and cemeteries retain
  separate subdued tones;
- water bodies, rivers, and water labels remain clearly legible;
- motorway, primary/trunk, secondary/tertiary, minor/service, tunnel, bridge, rail,
  and pedestrian layers retain distinct hierarchy;
- district, city, water, and road labels keep separate scale and opacity;
- POIs remain selective and subordinate to operational overlays;
- bloom and teal are not applied globally to the basemap.

The primary style remains a real remote vector style. The existing static
`GeoWorldFallback` is used only for WebGL or network/capability failure, not as the
normal desktop presentation.

## Provider Boundary

Add a renderer-neutral basemap configuration module that owns provider identity,
style URL, attribution, data provenance, credential requirements, and quality
tier. `PersistentGeoWorld` consumes this contract and continues to own only the
MapLibre lifecycle. `VITE_MAP_STYLE_URL` remains an explicit override and is
classified as a configured provider rather than silently inheriting OpenFreeMap
attribution.

The operational overlay contract remains independent. A future Google renderer
can consume the same city datasets and Deck layer factory through another host
adapter without changing courier, route, risk, selection, or LOD semantics.

## Routing Boundary

Basemap tiles do not own road-following courier geometry. The Compute travel
contract already carries optional `TravelTime.route_geometry`, and the bounded
`NetworkTravelProvider` returns deterministic shortest-path geometry, edge IDs,
and zones. The current Web Demo does not consume that backend geometry and the
current Google Routes adapter requests distance/duration without a polyline.

RM-249 therefore preserves deterministic synthetic city corridors and their
`DEMO / SYNTHETIC` provenance. A later API projection may supply renderer-neutral
route geometry independently of whichever visual basemap provider is active.

## Regression And Visual Gates

Automated coverage must verify provider metadata, attribution, style selection,
semantic theme classification, the exact Option B populations and emphasized
route counts, LOD membership, lens lifecycle, and map zoom controls. Format, lint,
typecheck, unit tests, production build, focused Playwright, and repository gates
must pass.

Browser review must cover Shanghai, Shenzhen, and Chengdu at overview, district,
and selected-courier states; pointer movement and rest; direct zoom; reduced
motion; desktop and narrower laptop widths; and continuous seven-chapter scroll.
The checkpoint fails if roads remain flat, labels become noisy, the operational
field becomes visual spaghetti, the lens disappears, attribution is inaccurate,
or the map falls back during a normal high-quality desktop load.

## Scope Boundaries

No Google credential, MapTiler credential, new billing dependency, national map,
H3 production pipeline, live rider telemetry, new backend API, production routing
claim, or calibrated Digital Twin state is introduced.
