# RouteMind Immersive Operations: Seven-Chapter Persistent Spatial World

**Date:** 2026-08-30
**Status:** Approved for implementation planning
**Scope:** Visual DOM and interaction composition of the React 19 Operations route

## Outcome

Recompose the complete Operations route into an immersive, scroll-driven
operational interface built from real RouteMind capabilities and data. The page
must remain usable as an operational workspace, but its primary structure is no
longer a dashboard card grid. Business capabilities become content placed into
seven sequential visual chapters, while one persistent Three.js world remains
mounted through the whole route.

The static composition must already look substantially redesigned. If all GSAP,
pointer, and continuous scene motion were disabled, the result must still read
as a RouteMind visual experience rather than the existing Operations dashboard.

This design keeps React 19, existing route behavior, `OperationsSnapshot`, source
and command contracts, accessibility, backend ownership, and test boundaries.
It does not copy Codrops branding, text, assets, or artwork. It adapts the
composition mechanisms from the supplied references: persistent world,
section-level parallax, stage hand-off, camera reframing, spatial overlap, and
local pointer inspection.

## Why the Previous Composition Is Rejected

The current checkpoint adds a sticky Hero, analytical strip, pointer lens, and
scroll progress to an unchanged dashboard hierarchy. Its content still reads as
sidebar + topbar + stacked panels, and removing animation reveals almost the
same layout. That violates the acceptance criterion for this correction pass.

The new implementation is therefore a visual DOM/layout re-composition, not a
motion pass on the existing `page-stack`. Existing components are treated as
capability renderers or data views that can be mounted inside new chapter slots.

## Scope and Non-Goals

In scope:

- Operations-only navigation and visual composition;
- one persistent UrbanFieldScene across all seven chapters;
- chapter-specific viewport composition, camera framing, scene layers,
  typography, analytical surfaces, HUD, and spatial depth;
- semantic pointer inspection shared by scene, charts, HUD, and controls;
- responsive desktop, laptop, and mobile compositions;
- reduced-motion and WebGL fallback that preserve the new static composition;
- browser-driven continuous-scroll visual quality evidence.

Out of scope:

- redesigning Strategy, Customer, Merchant, or Courier routes;
- production H3 ingestion, national globe, full Digital Twin calibration, or
  new backend APIs;
- Presentation Mode or persistent cross-route page transitions;
- moving durable business authority into the browser;
- replacing business data contracts or removing existing controls.

## Visual Composition Grammar

Every chapter must define a distinct composition contract before implementation.
Chapters may use different dominant axes, asymmetry, scale, overlap, negative
space, partial off-screen objects, and foreground/middle/background ratios. They
must not be the same viewport template with different headings.

Each chapter specifies:

- dominant visual anchor and its viewport position;
- UrbanFieldScene role: subject, background world, local inset, or inspection
  object;
- camera mode and depth range;
- typography scale, alignment, and entry edge;
- analytical surface mode: hero, floating, edge instrumentation, or docked;
- HUD density and focus target;
- foreground/middle/background layer allocation;
- hand-off source and destination from adjacent chapters;
- keyboard/readability fallback when motion is disabled.

The scene remains one mounted world, but its framing and material hierarchy make
each chapter feel like a different operational scene.

## Seven Chapters

### 1. Network Overview

Composition: central or slightly right-weighted city world occupying most of the
viewport, with large RouteMind identity typography entering from the left and a
compact operational readout floating low in the foreground. Navigation is a
thin rail, not a dominant sidebar. The scene is the subject; charts are absent
or reduced to two edge telemetry ticks.

Scene state: wide camera, high negative space, balanced ambient lighting, core
and route field at normal prominence. The intro and source state remain readable
without blocking the world.

### 2. Urban Pressure

Composition: asymmetric split with the world shifted left and closer to the
viewer. Demand/supply/risk instrumentation enters from the right at different
depths. Instanced cells become the foreground surface, while the intelligence
core moves into the middle distance. A pressure heatmap partially overlaps the
scene edge instead of appearing below it.

Scene state: lower camera angle, deeper field, stronger cell height contrast,
route ribbons receding in perspective, and focused demand/supply lighting.

### 3. SLA / Risk

Composition: risk is the visual anchor. A large risk trend and threshold line
occupy the left foreground; the world is visible behind and to the right with
hotspots enlarged. The previous overview typography recedes into a small upper
label. Risk annotations and the selected spatial zone overlap the scene without
covering critical controls.

Scene state: risk zones and route exposure are prominent, red/amber response is
selective, core deformation calms, and camera target moves toward the active
hotspot. The chart is `hero`, not a card.

### 4. Strategy

Composition: diagonal hand-off from risk field to a strategy instrument wall.
Strategy distribution and switching/RADS preview occupy the right foreground in
an offset stack; the world shifts left and becomes a responsive contextual
object. A large strategy statement sits between the scene and instrumentation,
with generous negative space around it.

Scene state: camera pulls back and rotates slightly toward the strategy axis;
core scale, route activity, and lighting respond to strategy state. Charts use
`floating` and `docked` modes at different progress intervals.

### 5. Live Operations

Composition: a wide inspection bay, not a panel grid. The persistent world is a
shallow background plane with the selected route/map enlarged in the foreground.
Order queue becomes a tall right-side inspection column; lifecycle timeline is a
horizontal route track crossing the lower third; dispatch activity appears as a
vertical event stream. The selected order detail is anchored near the route,
not in a separate generic card.

Scene state: camera focuses the selected order/route, non-selected layers dim,
route/node focus increases, and the core becomes a contextual beacon.

### 6. Simulation / Replay

Composition: the world becomes a replay viewport with a strong horizontal time
axis. Playback controls and scenario settings form a floating bottom dock. The
timeline is part of the scene composition, while metrics appear as compact
floating counters above the field. If the source is unavailable, the same
chapter remains structurally present with explicit unavailable/pending content.

Scene state: camera tracks replay time or simulation step, route flow and cell
waves become temporal signals, and scene lighting distinguishes captured replay
from deterministic simulation without claiming production telemetry.

### 7. Research / Reliability

Composition: the world recedes into a dark spatial backdrop while evidence
surfaces form an asymmetric research wall. Reliability invariants, analytical
layers, Decision X-Ray, lineage, and calibration status enter as connected
evidence objects rather than repeated cards. The chapter uses more negative
space and less motion, with a persistent focus rail for provenance and status.

Scene state: low-motion inspection mode, restrained lighting, stable camera, and
localized highlights for the selected evidence or dependency. The final scene
settles instead of looping theatrically.

## Persistent World Architecture

`OperationsExperience` owns the route composition. `UrbanFieldScene` is mounted
once inside `PersistentUrbanWorld` and receives immutable `UrbanFieldState` plus
imperative frame inputs. It is not nested inside a chapter that unmounts during
scroll.

The scene controller accepts a renderer-neutral chapter frame:

```ts
interface UrbanWorldFrame {
  chapter:
    | "overview"
    | "pressure"
    | "risk"
    | "strategy"
    | "live-operations"
    | "simulation-replay"
    | "research-reliability";
  progress: number;
  cameraMode: "wide" | "close" | "risk" | "strategy" | "inspection" | "stable";
  sceneRole: "subject" | "context" | "background" | "inset";
  layerVisibility: {
    cells: number;
    flows: number;
    riskZones: number;
    nodes: number;
    core: number;
  };
  focusStrength: number;
  lighting: { key: number; ambient: number; risk: number };
}
```

The adapter derives chapter inputs from existing `OperationsSnapshot`, current
selection, source mode, replay/simulation state, and the future `spatial`
extension on `UrbanFieldState`. It never invents production state.

## Component Boundaries

New composition primitives:

- `OperationsExperience`: route-level composition and chapter ordering;
- `OperationsNavigationRail`: Operations-only compact navigation and chapter
  progress;
- `PersistentUrbanWorld`: one scene mount, HUD, focus readout, and fallback;
- `OperationsChapter`: semantic chapter wrapper with visual composition metadata;
- `ChapterInstrumentation`: chart/metric surface that supports hero, floating,
  edge, and docked modes;
- `OperationsControlDock`: source, filter, simulation, replay, and inspection
  controls positioned by chapter without changing their command contracts;
- `OperationsMotionCoordinator`: shared scroll/pointer frame and lifecycle;
- `OperationsChapterAdapter`: snapshot-to-chapter semantic mapping.

Existing map, queue, timeline, activity, analytical, research, and reliability
components remain capability renderers. Their outer layout and placement may be
changed; their data contracts, control callbacks, labels, and keyboard paths are
preserved.

## Scroll, Pointer, and Scene Coordination

One `GSAP + ScrollTrigger` context is scoped to `OperationsExperience`. Native
scroll remains intact. The chapter track provides approximately one viewport of
progress per chapter, while the persistent world is sticky within the track.
There is no infinite scroll and no scroll-jacking.

The shared frame contains normalized scroll progress, active chapter, chapter
progress, signed velocity, pointer position/velocity, target type, target id,
inspection strength, and pressed state. React state is used only for semantic
focus and accessibility text; per-frame values stay in refs and CSS variables.

Pointer inspection targets include scene cells, routes, risk zones, core facets,
analytical regions, HUD, and controls. The lens is local to visual surfaces and
never distorts critical text or controls. RGB shift is zero at rest and only a
brief, capped response to higher-energy inspection or chapter hand-off.

## Navigation and Responsive Composition

Operations uses a compact rail or overlay utility navigation. At desktop widths
the rail occupies a narrow stable edge; at mobile widths it becomes the existing
drawer trigger and chapter indicator. The large legacy sidebar is not allowed to
consume the main visual field.

Desktop, laptop, and mobile use different compositions where necessary:

- desktop: asymmetric overlap and persistent sticky world;
- laptop: reduced scene detail with two-plane overlap and condensed rail;
- mobile: chapter-local flow with the world above or behind instrumentation,
  no horizontal overflow, and controls in a bottom dock.

Mobile is not a scaled desktop template. Off-screen decoration is clipped only
when it is nonessential; all business content remains reachable and readable.

## Accessibility, Reduced Motion, and Fallback

The redesigned composition preserves semantic DOM order and exposes every
chapter's content to assistive technology. Visual overlap never changes tab
order. Critical controls remain native elements and are excluded from transforms
that could move them under the pointer.

Reduced motion keeps the persistent WebGL world and renders the same seven
chapter compositions in stable layouts. It disables camera drift, deformation,
route flow, lens chromatic response, and large interpolated transitions. The
static composition remains redesigned and understandable.

WebGL fallback is used for capability failure or initialization failure only. It
renders the same chapter structure with a semantic spatial summary, not the old
dashboard layout.

## Performance and Cleanup

- one Three.js context and one scene RAF;
- one Operations scroll sampler and one pointer listener;
- capped DPR and bounded geometry/detail per breakpoint;
- no layout reads inside frame loops;
- GSAP context, ScrollTrigger instances, observers, listeners, and scene
  controller disposed on route change;
- chart surfaces use CSS transforms and SVG primitives already present in the
  application;
- no second full-screen WebGL context for pointer effects.

## Visual Quality Gate

The browser review rejects the implementation when any of these are true:

- disabling animation reveals essentially the old Operations dashboard;
- two or more chapters share the same main composition with only content swapped;
- the scene disappears or remounts between chapters;
- charts remain repetitive cards instead of becoming spatial instruments;
- later map/queue/timeline/research surfaces visibly fall back to ordinary BI
  panels;
- pointer lens reads as decoration rather than inspection;
- text, controls, chart axes, or keyboard focus become unstable.

The browser review must perform one continuous top-to-bottom scroll at 1280x720,
1024x768, and 760x800, plus fixed captures at each chapter hand-off. It must
inspect scene role changes, camera framing, chart hierarchy, navigation density,
pointer inspection, reduced-motion behavior, canvas pixels, console logs, and
horizontal overflow. The reviewer must also disable motion in-browser and judge
the static composition independently.

## Testing and Evidence

Focused tests will cover chapter mapping, chapter frame clamping, semantic
pointer target classification, reduced-motion frame behavior, persistent scene
mount count, fallback structure, control reachability, and route-level cleanup.
Existing Operations capability tests remain required.

Evidence will include the design-independent browser captures and a written
continuous-scroll observation. Build/test success is necessary but cannot close
the checkpoint without visual evidence.

## Implementation Invariants

The implementation must preserve:

- React 19 and current router/shell architecture;
- `OperationsSnapshot`, `UrbanFieldState`, source provenance, replay/simulation
  contracts, and command callbacks;
- existing map, queue, lifecycle, activity, analytical, research, and
  reliability capabilities;
- accessible labels, keyboard focus paths, unavailable/degraded states, and
  honest source-mode semantics;
- Java/Python/backend ownership boundaries and all unrelated worktree changes.
