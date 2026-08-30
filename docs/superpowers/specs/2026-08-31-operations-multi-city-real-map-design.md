# RouteMind Operations Multi-City Real Map Design

## Status

Approved design for the next Operations spatial checkpoint. This document is a
design boundary, not an implementation or production telemetry claim.

## Objective

Replace the current abstract Three.js city field with a real geographic
multi-city operations world for Shanghai, Shenzhen, and Chengdu. The selected
city must be switchable in the page while the existing seven-chapter immersive
Operations experience remains intact. The primary visual should immediately read
as couriers moving through a real city delivery network, with the map geography
and delivery semantics carrying more weight than decorative effects.

The implementation is limited to the frontend geographic/spatial layer and its
renderer-neutral adapter. It does not redesign backend contracts, add production
rider telemetry, implement production H3, expand the Digital Twin, or add
unrelated application routes.

## Architecture Decision

Use MapLibre GL JS as the geographic renderer and Deck.gl as the operational
overlay renderer. MapLibre owns the single geographic camera and one WebGL2
context. Deck.gl is attached with `MapboxOverlay({interleaved: true})` so map
labels, roads, risk regions, and operational layers share one rendering context
and depth hierarchy. React owns declarative configuration and lifecycle; refs and
the map/controller boundary own continuous camera and trajectory updates.

The official Deck.gl integration documents interleaved and overlaid MapLibre
integration and requires WebGL2 for interleaving:

- https://deck.gl/docs/developer-guide/base-maps/using-with-maplibre
- https://deck.gl/docs/api-reference/mapbox/mapbox-overlay

The default geographic style is OpenFreeMap's OpenMapTiles-backed style,
configured through an environment variable rather than a provider key embedded
in source. Attribution remains visible for OpenStreetMap and OpenMapTiles. The
style is replaceable by a self-hosted style or PMTiles-backed source without
changing the business-layer API. OpenFreeMap and PMTiles references:

- https://openfreemap.org/quick_start/
- https://docs.protomaps.com/pmtiles/maplibre

### Runtime layers

1. **Real basemap**: MapLibre vector tiles supply roads, water, district context,
   labels, and recognizable city geography.
2. **Operational overlays**: Deck.gl `GeoJsonLayer`, `HeatmapLayer` or
   `HexagonLayer`, `PathLayer`, `TripsLayer`, `ScatterplotLayer`, and selective
   `ArcLayer` represent risk, demand, supply, nodes, and movement.
3. **RouteMind chrome**: DOM HUD, city selector, legends, source/provenance,
   selected-entity details, and chapter instrumentation remain accessible outside
   the canvas.

Only one MapLibre instance and one Deck.gl overlay are created. The previous
abstract Three.js world is not used as a geographic substitute. Three.js may
remain elsewhere only when it provides a specialized non-map visual role that
does not duplicate the map context.

## Geographic City Catalog

Create a frontend `cityGeoCatalog` independent of the backend
`OperationsSnapshot`. Each entry contains:

- stable `cityId`, display name, and optional bilingual label;
- WGS84 `center`, `bounds`, and initial `zoom`, `pitch`, and `bearing`;
- a short geographic character and semantic corridor configuration;
- deterministic Demo seed and bounded route-generation parameters;
- base-style attribution and fallback metadata.

The initial contexts are:

| City | Geographic context | Demo movement character |
| --- | --- | --- |
| Shanghai (`shanghai`) | `121.4737, 31.2304`; Huangpu River and Pudong/Puxi relationship | Dense metropolitan flow with selective cross-river and cross-district routes |
| Shenzhen (`shenzhen`) | `114.0579, 22.5431`; elongated east-west urban structure | Longitudinal movement between multiple dense clusters and balancing corridors |
| Chengdu (`chengdu`) | `104.0668, 30.5728`; central density with ring/radial structure | Shorter repeated local deliveries with ring-like supply balancing |

The basemap provides real roads, water, and labels. Demo operational data is
deterministic, bounded, geographically located inside the selected city context,
and explicitly labeled `DEMO / SIMULATED operational data`. It never implies
real rider history or production telemetry. The three seeds and corridor
patterns must differ; identical percentage coordinates cannot be reused under
different city labels.

The compact city selector lives in the persistent world command chrome as a
keyboard-accessible segmented control. Switching city updates the map camera,
basemap context, overlay data, labels, attribution, pressure/supply/risk
context, and selected-entity validity without reloading the React app or creating
another rendering context. The current chapter remains selected. If an order or
courier is invalid in the new city, its selection is cleared and the DOM exposes
a concise unavailable state.

## Renderer-Neutral Spatial Contract

Extend the existing adapter without forcing MapLibre or Deck.gl types into the
domain model. The conceptual shape is:

```ts
spatial?: {
  city?: CityGeoContext;
  cells?: SpatialCell[];
  nodes?: SpatialNode[];
  flows?: SpatialFlow[];
  routes?: CourierTrajectory[];
  riskZones?: SpatialRiskZone[];
}
```

Exact names and field types follow repository conventions, but the contract must
preserve these semantics:

- geographic positions are WGS84 longitude/latitude pairs;
- cells carry stable ids, intensity, pressure/supply and optional risk;
- nodes distinguish courier, merchant, customer, hotspot, and risk entities;
- flows carry origin, destination, volume, ETA/risk and aggregation level;
- routes carry `courierId`, optional `orderId`, route state, points, timestamps,
  current segment, and optional metadata needed for selection;
- risk zones carry stable ids, geometry reference, severity, label, and selection.

The adapter can populate this contract from deterministic Demo data now and from
live, replay, or simulation sources later. Missing source fields remain explicit
as unavailable; the renderer must not fabricate live values.

## Courier Trajectory Grammar

Every primary visible path maps to an operational chain:

`courier current position -> merchant pickup -> customer delivery -> optional
next assignment/repositioning`.

Three route states are rendered:

- **Active**: strongest emphasis, direction marker, current position, pickup,
  destination, ETA and risk context. `TripsLayer` or a refs-driven equivalent is
  used only for actual simulation/replay progression or labeled Demo motion.
- **Recent**: reduced opacity and brightness with bounded, decaying retention;
  never permanent spaghetti.
- **Selected**: full semantic route and linked instrumentation for courier/order,
  lifecycle, ETA, distance, current task, SLA risk, and strategy.

At city overview scale, aggregate by district/corridor/operational zone and use
selective low-elevation `ArcLayer` or `PathLayer` flows. At city detail scale,
use near-road `PathLayer` geometry from order routes or deterministic corridors.
Airline-like curvature is reserved for long cross-district aggregate movement,
not every rider.

Fixed visual grammar:

- courier: directional mobile marker and status ring;
- merchant: pickup-origin marker;
- customer: delivery-destination marker;
- demand hotspot: heat/hex density field;
- courier supply: separate density or node layer;
- SLA risk: bounded GeoJSON fill, outline, label, and numeric/text status;
- traffic: restrained spatial overlay;
- selected entity: local halo/outline, tooltip, and linked panel focus.

There are no unexplained glowing spheres or decorative flight routes. Pointer
inspection is local and semantic: route/courier/merchant/customer/risk targets
receive restrained focus and contextual metadata. Native cursor behavior remains;
resting RGB separation is disabled and any pressed response is brief and bounded.

## Seven-Chapter Integration

The persistent map remains mounted through all chapters. Existing native scrolling
and GSAP coordination continue; there is no scroll-jacking. The chapter controller
updates MapLibre view state, Deck.gl layer props, aggregation/detail level, HUD
hierarchy, and analytical hand-off.

1. **Network Overview**: full selected-city bounds, high geographic context, low
   pitch, city identity, strategy, source state, summary metrics, and a few
   aggregate flows.
2. **Urban Pressure**: closer density framing, stronger demand heat/hex and supply
   layers, corridor detail, traffic pressure, and linked pressure/supply-gap
   analysis.
3. **SLA / Risk**: risk GeoJSON regions, delayed routes, ETA pressure, and selected
   risk-cell linkage to the SLA trend; ordinary routes recede.
4. **Strategy**: strategy-dependent flow distribution, repositioning, balancing,
   and switch state shown as edge instrumentation around the map.
5. **Live Operations**: closest operational view; selected courier's complete
   route chain is prominent while queue, lifecycle, activity, and metadata remain
   spatially connected.
6. **Simulation / Replay**: timeline, play/pause, seek and speed operate only on
   available simulation/replay state. Without data, show truthful pending/
   unavailable state and no invented movement.
7. **Reliability / Research**: calmer map context with risk distribution,
   experiment bounds, reliability invariants, lineage, scenario comparison, and
   calibration evidence in the foreground.

Adjacent chapter hand-offs blend camera center/zoom/pitch/bearing, layer opacity,
route aggregation, and HUD depth. City switching recalculates the current
chapter's camera template for the new city and preserves chapter index.

## Performance, Lifecycle, and Degradation

- MapLibre and Deck.gl are initialized once; city switching updates props and
  camera state instead of remounting.
- Memoize layer definitions and keep continuous movement in refs/rendering state;
  do not call React state setters every animation frame.
- Bound active, recent, and selected route counts; reduce path count, label
  density, heat resolution, and trip updates on narrow screens.
- Cap DPR at 1.5 using MapLibre `pixelRatio` and Deck.gl device-pixel controls.
- Pause trip/camera updates when the page is hidden; resume from the current state
  when visible.
- Under `prefers-reduced-motion`, keep the real map and static operational layers;
  freeze camera drift, trip pulses, chromatic response, and decorative movement.
- On WebGL2/map/style initialization failure, show a static geographic fallback
  with city label, DEMO/source status, summary metrics, and unavailable-map state.
  Never return to the old abstract orb.
- On unmount, finalize the overlay, remove the map, disconnect observers, remove
  listeners, cancel RAF/GSAP work, and release WebGL resources.

## Accessibility and Layout

City selection, current chapter, selected courier/order, route metadata, risk
status, source/provenance, DEMO/LIVE indication, and fallback state remain
keyboard and DOM accessible. Color is never the only risk/status signal. The map
canvas receives a meaningful label, and hover focus has an equivalent selected or
textual state.

At `1280x720`, `1024x768`, and `760x800`, the map retains priority while overlay
density reduces progressively. Critical controls move to compact edge/bottom
instrumentation on narrow screens. All shrinking grid/flex children use
`min-width: 0`; headings, legends and controls wrap; page overflow and accidental
horizontal scrolling are prohibited except for inherently non-reflowable local
timeline content.

## Browser Visual Gates

The implementation is incomplete until real browser inspection passes all gates:

- **A Geographic credibility**: each city visibly has real basemap geography,
  recognizable context, coherent bounds, and clear city identity.
- **B Trajectory semantics**: a viewer reads active lines as delivery riders,
  pickup/drop-off routes, and supply movement rather than aircraft or decoration.
- **C City switching**: Shanghai -> Shenzhen -> Chengdu -> Shanghai updates map,
  camera, Demo data, routes, labels and validity while preserving chapter.
- **D Continuous scroll**: each city is scrolled through all seven chapters; the
  persistent world changes role without returning to an old card-grid dashboard.
- **E Layout integrity**: all three required viewports have no clipping,
  accidental horizontal overflow, overlay collision, or unusable control.
- **F Motion disabled**: with GSAP/pointer motion disabled, the static result is
  still an immersive real-city Operations environment.

Capture evidence for all cities, at least one selected courier, city switching,
continuous scroll, reduced motion, multi-viewport layout, and console output.

## Testing and Evidence

Add focused tests for city catalog uniqueness, deterministic seed output,
city-specific trajectory differences, invalid-selection clearing, reduced-motion
retaining the map, map lifecycle cleanup, and chapter persistence. Run format,
lint, typecheck, focused and full unit suites, build, targeted and full relevant
Playwright suites, and browser visual gates.

Evidence must record map style/source and attribution, the Demo disclaimer, all
visual gate results, screenshots, automated output, and known limitations. Do not
claim production rider telemetry, real courier history, external provider
qualification, production H3, or calibrated Digital Twin state without matching
evidence.

## Implementation Order

1. Audit current map/Three.js/visualization stack and freeze the boundary.
2. Add the city catalog and renderer-neutral spatial contract.
3. Add MapLibre base map and one Deck.gl overlay lifecycle with fallback.
4. Generate deterministic, city-specific Demo operational data.
5. Implement courier trajectory layers, selection, and semantic inspection.
6. Add keyboard-accessible city switching with current-chapter persistence.
7. Integrate the persistent map into the seven chapter controller.
8. Recompose analytical overlays around geography and selected routes.
9. Add scroll/camera/aggregation choreography and reduced-motion behavior.
10. Run intermediate browser Gates A-C before polishing.
11. Fix responsive layout and run Gates D-F across all viewports.
12. Run automated suites, record evidence, self-review claims, then create one
    coherent checkpoint commit and push only after all visual gates pass.

## Scope Guard

This checkpoint does not include a national globe, full Digital Twin, production
H3 pipeline, Decision X-Ray expansion, Presentation Mode, production map provider
qualification, or real rider telemetry ingestion. It is a frontend real-map and
deterministic Demo-trajectory foundation designed for those later extensions.
