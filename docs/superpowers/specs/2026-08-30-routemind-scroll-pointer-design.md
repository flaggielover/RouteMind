# RouteMind Operations Scroll and Pointer Interaction Design

**Date:** 2026-08-30
**Scope:** Phase 1 scroll-driven spatial narrative and semantic pointer inspection for the existing React 19/Vite Operations surface

## Goal

Extend the existing RouteMind visual foundation so the complete Operations page
feels like one operational environment rather than a WebGL hero followed by
disconnected dashboard panels. Native browser scrolling remains the source of
truth for navigation. Scroll progress, pointer inspection, the Three.js scene,
analytical surfaces, HUD labels, and section emphasis are coordinated through a
single rendering-layer interaction model.

The result should feel like moving through operational layers: overview,
spatial field, risk and demand, strategy and analytics, then deeper map, queue,
timeline, activity, simulation/replay, and research surfaces. The page keeps
its existing content order, route boundaries, business APIs, and keyboard
interaction semantics.

## Safe Ownership Boundary

This checkpoint is limited to:

- `apps/web/src` motion coordinator, pointer state, scene controller additions,
  analytical interaction hooks, styles, and focused tests;
- `apps/web/package.json` and `package-lock.json` only when the chosen motion
  runtime requires a minimal dependency;
- this design note and browser evidence under `docs/` and `evidence/`.

It does not modify backend contracts, event schemas, persistence, infrastructure
lifecycle scripts, other product routes, or files owned by the concurrent PR-001
business/API line. The motion system is mounted only by `OperationsView`.

## Design Principles

1. **One operational space.** Every Operations section participates in the same
   progress and focus model. Hero and analytical sections receive stronger
   camera/depth transitions; map, queue, timeline, activity, simulation, replay,
   and research panels use restrained hand-off and layering so the page never
   drops back to an unrelated dashboard language.
2. **Native scroll remains intuitive.** The browser owns wheel, trackpad,
   keyboard, anchor, and touch scrolling. Pinning is bounded to visual stages and
   never prevents a user from reaching or activating controls.
3. **Inspection over decoration.** Pointer response communicates what is being
   inspected: nearby cells, routes, risk zones, core facets, or analytical
   regions become clearer. Chromatic shift is an occasional, low-amplitude energy
   cue, never a permanent glitch layer.
4. **Shared frame, not shared React renders.** Scroll and pointer samples live in
   mutable refs and are consumed by the DOM and Three.js rendering layers from a
   single RAF coordinator. React state is reserved for semantic focus changes,
   accessibility text, and user actions.
5. **Readable at rest.** Effects settle to a stable composition. Critical text,
   metrics, charts, controls, and keyboard focus are never transformed by the
   lens layer or moved away from the interaction target.

## Motion Runtime

The recommended runtime is `GSAP + ScrollTrigger` scoped to `OperationsView`.
ScrollTrigger provides scrubbed section progress, bounded pinning, velocity,
and focus hand-off while leaving the browser's scroll model intact. Lenis and
infinite scroll are intentionally not used: an operational workspace must have
predictable page length, native touch behavior, and reachable deep panels.

If dependency review rejects GSAP, the coordinator keeps a native fallback based
on `IntersectionObserver`, a single RAF sampler, and CSS custom properties. The
fallback preserves content order and all semantic states, with reduced pinning
and simpler interpolation.

The implementation adapts techniques rather than copying demos. The Codrops
Infinite Scroll material demonstrates section-level parallax and controlled
handoff; the Pointer Lens material demonstrates a local mask, eased pointer
movement, center-stable distortion, and edge-weighted RGB shift. RouteMind maps
those mechanisms to operational state instead of image-gallery semantics:

- [Codrops Infinite Parallax](https://tympanus.net/codrops/2026/05/28/the-never-ending-story-building-a-seamless-infinite-scroll-experience-with-gsap-lenis/)
- [Codrops Pointer Lens](https://tympanus.net/codrops/2026/08/25/building-a-mouse-following-square-lens-effect-with-three-js-and-glsl/)
- [Codrops Interactive 3D Cluster](https://tympanus.net/codrops/2026/08/12/creating-an-interactive-3d-cluster-with-three-js-tsl-and-three-start/)
- [Codrops Wave Propagation Cube Grid](https://tympanus.net/codrops/2026/07/09/building-an-interactive-wave-propagation-cube-grid-with-three-js/)
- [Codrops Cinematic 3D Scroll](https://tympanus.net/codrops/2025/11/19/how-to-build-cinematic-3d-scroll-experiences-with-gsap/)

## Full Operations Composition

`OperationsView` will render an `OperationsMotionCoordinator` around the
existing page stack. Sections opt into motion through data attributes rather
than bespoke listeners:

| Layer | Existing content | Scroll role | Visual hand-off |
| --- | --- | --- | --- |
| Overview | page intro, filters, source/projection state | establish context | topbar and intro remain stable; scene enters with depth |
| Spatial field | UrbanFieldScene and semantic rail | bounded sticky stage | core, cells, routes, and HUD carry the primary focus |
| Risk / demand | analytical strip and heatmap | scrubbed focus beat | core deformation calms; risk threshold, heatmap, and local cells gain emphasis |
| Strategy | strategy distribution, health, metric grid | focus hand-off | camera eases back; strategy comparison and latency readout move forward |
| Operations detail | map, order queue, lifecycle timeline, dispatch activity | layered reveal | scene becomes a contextual backdrop; selected order/route receives depth and halo |
| Simulation / replay | controls and twin visualization when present | state-aware transition | replay cursor or simulation activity becomes the active visual signal |
| Research / reliability | analytical layers, Decision X-Ray, reliability panels | settle into inspection | effects reduce to subtle parallax and active evidence emphasis |

The first three layers may share a sticky visual stage of roughly two viewport
heights. Later sections remain in normal flow but are animated with bounded
translate/scale/opacity/depth values. No panel is hidden solely because it is
outside the strongest focus beat, and no content is duplicated for an infinite
loop.

The coordinator exposes stable CSS variables on the Operations root:

- `--rm-scroll-progress`: normalized whole-page progress;
- `--rm-section-progress`: progress within the active section;
- `--rm-scroll-velocity`: clamped signed velocity;
- `--rm-focus-strength`: active section emphasis;
- `--rm-pointer-x`, `--rm-pointer-y`, `--rm-pointer-intensity`.

Each section also receives a semantic focus class/attribute at threshold
crossings. This lets CSS, chart wrappers, HUD labels, and the scene share one
hierarchy without React updates on every frame.

## Unified Pointer Contract

The coordinator owns one mutable pointer object:

```ts
interface RouteMindPointerState {
  x: number;
  y: number;
  nx: number;
  ny: number;
  vx: number;
  vy: number;
  intensity: number;
  targetId: string | null;
  targetType: "scene" | "chart" | "hud" | "control" | null;
  pressed: boolean;
}
```

Pointer events are attached once to the Operations interaction root. The target
is resolved with `closest("[data-pointer-target]")`, with controls marked as
non-distorting targets. Velocity is smoothed and clamped; a quick movement may
raise inspection energy briefly, then decays to a stable value.

`UrbanFieldScene` receives the same frame through an imperative controller ref.
Its existing raycast projection maps the pointer to world space and now uses
the shared target/energy to:

- magnify or brighten nearby spatial cells and risk zones;
- emphasize a route ribbon or node under inspection;
- deform nearby intelligence-core facets within a bounded radius;
- adjust camera parallax and local wave propagation;
- expose the focused entity through the existing accessible live summary.

Analytical wrappers opt into `data-pointer-target="chart"` and provide local
point/region focus, tooltip detail, threshold lines, or a halo. They never
distort critical labels or axes. HUD and control targets may show a focus ring,
but the lens overlay is disabled over clickable controls.

## Lens and Distortion Layer

The lens is integrated into the existing UrbanFieldScene post-processing chain,
not implemented as a second full-screen WebGL context. A small shader pass (or
equivalent bounded material uniform) receives eased pointer position, lens
radius, inspection intensity, and RGB shift amount.

- Lens strength is zero at rest and rises only when the pointer is over a scene,
  chart region, or semantic spatial target.
- Distortion is local to scene/visual surfaces; text, buttons, form controls,
  and focus outlines are outside the effect layer.
- The center of the lens remains visually stable; refraction grows toward the
  local edge, following the reference technique.
- RGB shift is normally disabled and is capped to a short-lived, very small
  value during high pointer velocity or a focus transition.
- On constrained devices, touch input, or reduced motion, the lens becomes a
  static focus halo without animated chromatic displacement.

## Three.js Scene Coordination

The current renderer lifecycle remains authoritative: one canvas/context,
ResizeObserver sizing, DPR cap, visibility/in-viewport pause, reduced-motion
mode, and complete disposal. The new scene controller adds only frame inputs:

```ts
interface UrbanFieldSceneController {
  setScrollFrame(frame: { progress: number; section: number; focus: number }): void;
  setPointerFrame(pointer: RouteMindPointerState): void;
  clearFocus(): void;
  dispose(): void;
}
```

Scroll changes alter camera target, scene scale/depth, core deformation factor,
route flow intensity, and which spatial layer carries emissive emphasis. The
controller clamps all values and settles smoothly, so stopping the page leaves
a coherent stable composition. The scene does not know about React routes or
business commands; it consumes `UrbanFieldState` plus frame inputs.

The renderer-neutral `UrbanFieldState.spatial` extension remains the future
contract for cells, nodes, flows, and zones. The motion layer does not require
H3 today and can later map the same focus/inspection model to real spatial
collections.

## Reduced Motion and Fallback

`prefers-reduced-motion` never forces `GpuSceneFallback`. WebGL remains visible
with a stable field, readable labels, and semantic hover/focus. Continuous
camera drift, deformation, route flow, pulses, scroll parallax, and chromatic
shift are disabled or frozen. Section ordering, controls, charts, and deep
panels remain fully usable.

Fallback is used for WebGL unavailability, renderer initialization failure, or
equivalent capability failure. The static fallback receives the same state and
semantic summary and does not rely on motion to communicate risk or status.

## Performance and Cleanup

- One page-level pointer listener, one scroll sampler, and one RAF coordinator.
- No React state writes in the frame loop; semantic focus changes are thresholded.
- GPU transforms use `transform`/opacity and bounded shader uniforms; no layout
  reads inside the animation loop.
- ScrollTrigger and GSAP contexts are created inside the Operations effect and
  reverted on unmount or route change.
- ResizeObserver, IntersectionObserver, visibility listeners, renderer frames,
  and controller refs are all cleaned up together.
- DPR and scene detail remain capped; narrow screens reduce visual detail while
  retaining field legibility.

## Accessibility and Readability

Native controls retain their DOM position and focus order. The pointer overlay
uses `pointer-events: none`. Keyboard users receive the same semantic focus
summary and can inspect chart/scene entities through existing list or control
representations. Risk, freshness, source mode, and fallback status remain
communicated as text and labels in addition to color or motion.

## Visual Quality Gate

Browser inspection is a required acceptance step, not a postscript to tests.
At 1280x720, 1024x768, and 760x800, the reviewer will:

1. Capture top, spatial, analytical, detail, simulation/replay, and deep
   research states.
2. Perform one continuous scroll from the top to the bottom at normal wheel or
   trackpad cadence, without jumping between fixed offsets.
3. Observe whether section focus hands off naturally, whether the Three.js scene
   changes visual role over time, and whether charts, HUD, pointer inspection,
   and panel layering read as one system.
4. Move the pointer slowly across cells, routes, core facets, chart regions, and
   controls, then perform a short faster gesture to verify semantic inspection
   and restrained transient RGB response.
5. Repeat with reduced motion and verify that the page remains readable and
   useful without continuous animation.

The checkpoint is rejected if continuous scrolling still feels like a collection
of independent pages, if the scene reads as a generic rotating object, if any
effect harms chart/text readability, or if the page becomes visually tiring.

## Testing and Evidence

Focused tests cover pointer smoothing/target classification, scroll progress
clamping, reduced-motion frame behavior, scene-controller cleanup, and existing
Operations rendering. Browser evidence records console errors, canvas pixels,
horizontal overflow, source/fallback labels, and continuous-scroll observations
at all three viewports. Existing unit, type, lint, build, and e2e gates remain
required; passing those gates alone is not sufficient for this checkpoint.

## Non-Goals

This checkpoint does not add infinite scroll, persistent page transitions across
routes, a national globe, production H3 ingestion, a full Digital Twin, a new
backend API, Presentation Mode, or a Decision X-Ray redesign.
