# RM-247 Deterministic Courier Density and LOD Design

Date: 2026-08-31  
Status: Approved for implementation  
Scope: Operations Demo geospatial visualization only

## Objective

Increase the deterministic Demo operational field from six visible active riders
to a credible city-scale courier population without turning the real-city map into
visual noise. The implementation remains explicitly synthetic and must not imply
production telemetry, calibrated Digital Twin state, or provider validation.

The approved fixed populations are:

- Shanghai: 120 couriers and 32 emphasized trajectories.
- Shenzhen: 90 couriers and 26 emphasized trajectories.
- Chengdu: 104 couriers and 28 emphasized trajectories.

The existing Codrops-derived optical pointer lens remains part of the same
MapLibre WebGL composition. Its size changes from 39% of the short viewport edge,
clamped to 220-330 px, to 29%, clamped to 170-240 px. Distortion, tracking,
velocity-sensitive RGB separation, UI exclusion, reduced-motion behavior, and
cleanup remain unchanged.

## Data Contract

`CityOperationalDataset` separates two concepts:

1. `courierAgents` is the complete synthetic city population. Every agent has a
   stable ID, deterministic corridor/path binding, base progress, speed, risk,
   state, heading source, and optional emphasized trajectory relationship.
2. `trajectories` contains the smaller selectable route set with courier, order,
   merchant, customer, ETA, distance, SLA risk, strategy, and full path semantics.

All generated properties derive only from the existing stable city seed plus
stable numeric namespaces. Dataset construction does not depend on wall time,
random APIs, React render order, or browser state. Animation adds render-loop time
to the immutable base state and never mutates the dataset.

Route variants reuse the hand-authored city road corridors and add small,
deterministic, bounded lateral offsets to intermediate points. Endpoints remain
anchored to the merchant and customer nodes. Every generated coordinate must stay
inside the configured WGS84 city bounds.

Provenance remains `deterministic-demo`, and the map HUD uses the explicit label
`DEMO / SYNTHETIC`.

## LOD Contract

LOD is a pure renderer-neutral projection derived from the dataset, camera zoom,
chapter focus, and selected trajectory. It returns the exact courier and trajectory
members rendered by Deck.gl.

### City overview

- Render the complete courier population as small, low-opacity moving agents.
- Keep aggregate inter-district flows dominant.
- Render all emphasized trajectories as thin, restrained route bundles with no
  broad glow, preserving city network structure without creating visual spaghetti.
- Only emphasized routes and their bound couriers are pickable.

### District/focused view

- Select 10-16 deterministic context-relevant trajectories using distance to the
  current chapter focus plus stable risk and ID tie-breaking.
- Render the local trajectory subset more legibly and retain only couriers within
  a bounded focus radius plus the couriers bound to those routes.
- Lower aggregate-flow dominance while increasing local path hierarchy.

### Selected courier

- Always retain the selected courier and its merchant/customer endpoint semantics.
- Render the selected route at full emphasis.
- Retain up to four nearby contextual trajectories and a bounded neighborhood of
  nearby couriers; all unrelated city-wide routes disappear.
- Selection membership is deterministic and remains stable between renders.

The underlying population is never reduced to solve clutter. Browser iteration may
adjust marker opacity, size, focus radius, or visible LOD membership while the fixed
population counts remain intact.

## Rendering and Lifecycle

- Continue using the existing interleaved Deck.gl/MapLibre WebGL pipeline.
- Courier movement stays in refs and the existing throttled render loop. No React
  state update occurs per animation frame.
- Use one lightweight population marker layer, separate focus-ring and emphasized
  glyph layers, and existing route/flow layers. Low-emphasis agents are not
  individually labeled.
- Recompute LOD membership only when city, chapter/camera focus, zoom bucket,
  selection, or hover relationship changes.
- Preserve DPR limiting, visibility pause, reduced-motion freeze, map disposal,
  overlay finalization, and the single optical-lens layer.

## HUD and Interaction

The map summary truthfully exposes:

- total synthetic courier population;
- total emphasized trajectory count;
- current LOD (`CITY`, `DISTRICT`, or `SELECTED`);
- existing city and risk-zone context.

The selected-courier panel continues to expose courier to order, merchant/customer,
ETA, distance, SLA risk, and strategy semantics. The native cursor and optical
inspection lens remain available over the geographic world and excluded over HUD
or controls.

## Failure and Accessibility Behavior

The existing static fallback receives the richer dataset but remains bounded and
does not attempt to draw every route. Reduced motion freezes all courier positions
while retaining the same population and LOD truth in the rendered frame. City
switches clear stale selection and construct the exact deterministic population for
the destination city.

## Verification

Automated gates cover:

- repeatable dataset equality and stable IDs;
- exact 120/90/104 courier counts and 32/26/28 trajectory counts;
- generated coordinate and offset bounds;
- trajectory-to-agent and endpoint relationships;
- city, district, and selected LOD membership/count limits;
- selected-route isolation and contextual-neighbor bounds;
- city switching, HUD truth, reduced motion, one canvas, and preserved optical lens.

Browser gates inspect Shanghai, Shenzhen, and Chengdu at city overview,
district/focused, and selected-courier states. Evidence must show that each city is
visibly active, that focused views become clearer rather than denser, and that the
selected route is semantically isolated. Console, overflow, motion fatigue, lens,
and continuous-scroll checks remain required.

## Implementation Plan

1. Add the courier-agent contract, fixed city density specification, deterministic
   route variants, and pure LOD projection with focused unit tests.
2. Recompose Deck.gl layers into low-emphasis population, context routes, focused
   courier glyphs, and selected-route layers without React frame updates.
3. Add zoom/focus-aware LOD updates and truthful HUD diagnostics.
4. Apply the approved pointer-lens size reduction without changing its shader or
   lifecycle.
5. Extend component and Playwright gates for density, LOD, city switching, selected
   isolation, reduced motion, and lens preservation.
6. Run real-browser three-city visual iteration, preserve screenshots/evidence,
   execute repository gates, then create and push one coherent checkpoint.

## Explicit Non-Goals

- Production courier telemetry or production-scale performance claims.
- H3/geohash ingestion, calibrated demand, or a complete Digital Twin.
- Backend API changes, dispatch-authority changes, or durable synthetic records.
- New map providers, additional canvases, or a replacement pointer effect.
