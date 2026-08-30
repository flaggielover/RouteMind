# RouteMind Frontend Visual Foundation Design

**Date:** 2026-08-30  
**Scope:** Phase 1 visual foundation for the existing React 19/Vite web application

## Goal

Establish a premium operational visual foundation for RouteMind without changing
the frontend framework, backend contracts, route ownership, or infrastructure
lifecycle behavior. The Operations surface will gain a real WebGL centerpiece:
an urban spatial field that expresses demand, supply, route flow, and risk as a
coherent operational scene rather than decorative animation.

The design keeps the existing React 19 shell and typed `OperationsSnapshot`
boundary. It introduces native Three.js as the rendering kernel and isolates its
lifecycle inside a React component so a later Digital Twin renderer can replace
the scene without changing the page contract.

## Safe Ownership Boundary

The checkpoint is limited to:

- `apps/web/src` visual components, hooks, styles, and focused tests;
- `apps/web/package.json` and `package-lock.json` only for the minimal Three.js
  dependency if it is not already present;
- a concise visual architecture note and evidence under `docs/`.

The checkpoint will not modify PowerShell lifecycle scripts, Docker orchestration,
CI workflow semantics, repository verifiers, backend APIs, event schemas,
persistence models, or files already owned by the concurrent PR-001 line.

## Product Composition

The existing `AppShell` remains the route and data boundary. The Operations page
will be composed as a dense command workspace:

1. A compact operational top bar retains the current source, identity, realtime,
   health, and refresh controls. Visual treatment is upgraded through shared
   tokens, not by changing their behavior.
2. The hero workspace puts the `UrbanFieldScene` at the visual center. A narrow
   contextual rail exposes current mode, strategy, and scene legend; metric
   panels remain readable and keyboard-accessible around the scene.
3. Existing map, queue, timeline, activity, simulation, replay, and analytical
   panels remain available below or beside the hero according to the current
   responsive layout. They continue consuming their existing snapshot and
   command interfaces.
4. Demo, replay, and simulation sources are explicitly labeled as non-production
   in the shell and hero context. Live source availability remains truthful; no
   fabricated production state is introduced.

## Analytical Visualization Foundation

RouteMind is not a 3D-only operations page. Alongside the WebGL scene, Phase 1
establishes a small, reusable analytical visualization layer for the existing
React surface. The audit found no ECharts, Recharts, D3, or other general-purpose
chart dependency in `apps/web`; current visuals are bespoke CSS/SVG primitives.
The first implementation will therefore extend those local primitives with a
shared SVG-based chart toolkit rather than add a second chart library solely for
generic defaults.

The toolkit will provide tokenized wrappers and primitives for axes, gridlines,
legends, labels, tooltips, focus states, and empty/unavailable states. It will
demonstrate representative Operations views next to `UrbanFieldScene`:

- a live operational throughput/latency time-series;
- an SLA/risk trend with explicit risk thresholds;
- a strategy comparison/distribution view;
- a compact latency-versus-throughput readout;
- one richer zone-by-metric heatmap surface.

Charts share the graphite/slate surfaces, typography, state colors, motion
timings, tooltip behavior, and information hierarchy of the Three.js layer. They
must not use default ECharts/BI styling. Their renderer-neutral data contracts
are deliberately compatible with future Pareto frontiers, Strategy x Scenario
heatmaps, RADS/RADS-H switching timelines, Twin calibration, What-if deltas,
Reliability Invariant matrices, research lineage DAGs, VRPTW windows, replay
timelines, migration/resource flows, and operational SLA/risk/throughput/
latency series. Phase 1 only wires the representative Operations examples and
keeps their values clearly sourced from the existing snapshot or isolated demo
state.

## UrbanFieldScene API

The reusable component will accept a small, renderer-neutral view model:

```ts
interface UrbanFieldState {
  mode: "live" | "demo" | "replay" | "simulation";
  pressure: number;       // order pressure, normalized 0..1
  supply: number;         // courier supply, normalized 0..1
  risk: number;           // SLA risk, normalized 0..1
  traffic: number;        // congestion, normalized 0..1
  strategy: string;
  twinFidelity: number;   // 0..1, when available
  activityRate: number;   // event/solver activity, normalized 0..1
  spatial?: {
    cells?: readonly { id: string; center: GeoPoint; intensity: number; risk?: number }[];
    nodes?: readonly {
      id: string;
      kind: "order" | "courier" | "merchant" | "risk";
      position: GeoPoint;
      value?: number;
      risk?: number;
    }[];
    flows?: readonly {
      id: string;
      from: GeoPoint;
      to: GeoPoint;
      value: number;
      risk?: number;
    }[];
    zones?: readonly { id: string; center: GeoPoint; radius: number; risk: number }[];
  };
}
```

The adapter from `OperationsSnapshot` to this model is isolated from the
renderer. It may use deterministic demo values when a source does not provide a
field, and must label those values as visual demo state. The component exposes
optional `onFocusEntity` and `onSceneReady` hooks for future drawers, decision
x-ray links, and Digital Twin controls; Phase 1 does not invent new backend
endpoints. The optional spatial collections follow existing `GeoPoint` and
readonly-array conventions. They remain absent for Phase 1 demo data, but their
presence does not require replacing the component API when H3/geohash cells,
spatial nodes, flows, or risk zones arrive later.

## WebGL Scene Design

The scene is intentionally a spatial system, not a generic rotating object:

- A low-poly isometric city field provides a readable ground plane with layered
  height bands. Height and density respond to `pressure` and `traffic`.
- Instanced or pooled node geometry represents demand clusters, courier supply,
  merchants, and risk hotspots. Node color and pulse cadence have explicit
  semantic mappings.
- Curved route ribbons connect active clusters. Their width and restrained flow
  motion represent throughput and activity, while risk routes shift toward amber
  or red.
- A faceted central intelligence core anchors the scene. It uses physically based
  material response, controlled emissive accents, and subtle deformation driven by
  `pressure`, `risk`, and `activityRate`; it is not the only visual object.
- Directional, ambient, and point lights establish depth across the field. A
  restrained post-processing pass (bloom or equivalent, only when supported)
  reinforces active signals without washing out labels or creating a neon theme.
- Pointer movement produces bounded camera parallax and entity hover focus.
  Hover changes outline/emissive emphasis and updates an accessible textual
  context region; it does not communicate essential information only through
  motion.

The visual palette uses graphite, charcoal, and slate operational surfaces with
restrained teal/cyan active-data accents, amber warnings, and red risk states.
Teal/cyan never becomes the dominant field color. CSS variables define colors,
surfaces, elevation, blur, spacing, radii, and motion timings so the scene and
analytical panels share one language. Bloom/glow is selective and signal-driven:
it is applied only to active routes, focused nodes, or risk pulses, never as a
global dashboard treatment.

## React and Three.js Lifecycle

`UrbanFieldScene` owns one canvas and one Three.js renderer per mounted instance.
Initialization occurs in an effect after the container is measurable. The scene
uses a capped device pixel ratio, `ResizeObserver`, and a single animation loop.
The loop pauses while the document is hidden or the canvas is outside the viewport
when practical. Cleanup cancels the frame, disconnects observers/listeners,
disposes geometries/materials/textures/render targets, removes the renderer DOM
node, and releases references so route changes cannot leak WebGL contexts.

The heavy scene is lazy-loaded at the Operations hero boundary. Import or
initialization failures render `GpuSceneFallback`, a static semantic spatial
summary using the same `UrbanFieldState` values. The fallback is selected when
WebGL is unavailable or an equivalent capability fails; it is not selected merely
because reduced motion is requested. The fallback keeps the scene legend, key
metrics, and keyboard focus path intact.

`prefers-reduced-motion` disables camera drift, deformation, route flow, and
continuous pulses while retaining the WebGL scene in a stable, inspectable
configuration. Users can still focus entities and read state descriptions.

## Performance and Responsiveness

- Cap DPR (for example, 1.5 on desktop and 1 on constrained devices).
- Keep geometry counts bounded and prefer instancing/pooling over per-frame
  allocation.
- Avoid React state updates inside the render loop; scene animation reads a
  mutable view-model ref and only dispatches semantic focus changes.
- Recompute camera and renderer size through `ResizeObserver`, not every frame.
- Respect reduced-motion and visibility pause; do not create multiple contexts.
- At narrower widths, reduce node count and scene detail while preserving the
  central field, mode badge, metrics, and controls. Panels stack without overlap.

## Accessibility

The canvas has an accessible label and is paired with a live semantic summary.
Primary mode/source controls remain native buttons/selects with visible focus
states. Hoverable entities also have keyboard-reachable list representations, and
all risk/health states use text and icon/label combinations in addition to color.
Contrast follows the existing web gate expectations. No required action depends
on pointer-only interaction or animation.

## Testing and Evidence

Focused tests will cover:

- Operations shell and hero rendering with demo data;
- mapping from snapshot values to `UrbanFieldState`;
- WebGL-unavailable and initialization-error fallback;
- reduced-motion behavior and accessible scene summary;
- cleanup on unmount and no duplicate canvas/context creation at the component
  boundary;
- existing major routes remain reachable.

Verification will run the web unit suite, typecheck, lint, format check, and
production build. The existing Playwright suite will inspect a desktop and a
narrower laptop/mobile viewport, including console errors, source-mode labels,
fallback behavior, and visible scene composition. Infrastructure lifecycle
processes owned by PR-001 will not be restarted or terminated for this work.

## Visual Quality Gate

This checkpoint is not complete when tests and builds are green alone. After the
browser implementation, the visual review must capture evidence at a standard
desktop viewport and a narrower laptop viewport, then compare the actual result
against the supplied Codrops Interactive 3D Cluster reference direction. The
review explicitly evaluates spatial depth, composition, lighting, material
response, motion restraint, hover interaction, analytical information density,
and overall polish. If the result reads as a flat mock, generic rotating object,
basic Three.js sample, or conventional dark admin dashboard, implementation must
iterate before the checkpoint can be declared passed.

## Future Integration Points

The renderer-neutral state model leaves explicit slots for live order pressure,
courier supply, SLA risk, traffic incidents, RADS strategy state, twin fidelity,
replay time, Decision X-Ray selection, and H3/geohash fields. Later phases can
replace the adapter or add spatial layers without rewriting the shell or moving
business authority into the browser.

## Non-Goals

This checkpoint does not implement a national globe, production H3 rendering,
full Digital Twin simulation, complete Presentation Mode, Decision X-Ray
redesign, backend/API changes, or a framework migration.
