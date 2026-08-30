# RouteMind Immersive Operations Implementation Plan

**Design:** `docs/superpowers/specs/2026-08-30-routemind-immersive-operations-design.md`
**Date:** 2026-08-30
**Status:** Ready for implementation after plan approval

## Delivery Strategy

Implement the Operations route as a new visual composition layer around the
existing business capability components. The work is intentionally staged so a
working chapter shell exists before Three.js and chart details are migrated.
No backend, route contract, or non-Operations surface changes are permitted.

The first implementation checkpoint should be reviewable after the chapter
shell and persistent world are in place. The final checkpoint requires browser
continuous-scroll evidence and a static-composition review with motion disabled.

## Approved Execution Amendments

The controlling execution order is:

1. renderer-neutral contracts;
2. minimal `OperationsExperience` and chapter shell;
3. persistent world mount, stacking model, sticky stage, and controller boundary;
4. seven distinct static chapter compositions;
5. analytical surface recomposition;
6. scroll and semantic pointer choreography;
7. responsive and reduced-motion behavior;
8. final automated and browser gates.

Three browser gates run before the final gate:

- Gate A, after the shell and persistent world: the old dashboard skeleton must
  be absent, the world must mount once, and the sticky spatial composition must
  remain usable.
- Gate B, after Overview, Urban Pressure, and SLA/Risk: inspect all three in a
  real browser with motion enabled and disabled. Repeated viewport composition
  is a blocking implementation failure.
- Gate C, after all seven static compositions: disable GSAP and pointer effects.
  The frozen route must already be an immersive redesign before choreography is
  finalized.

After RM-240 passes every automated and browser visual gate, create one coherent
standalone commit. If the configured GitHub remote is authorized and healthy,
push that checkpoint automatically. If access or authorization fails, preserve
the local commit and record the exact blocker. Never push a partially verified
or visually failed checkpoint.

## Phase 1: Freeze Baseline and Add Semantic Contracts

Files:

- `apps/web/src/visuals/operationsChapterState.ts` (new)
- `apps/web/src/visuals/operationsChapterState.test.ts` (new)
- `apps/web/src/visuals/urbanFieldState.ts`
- `apps/web/src/components/UrbanFieldScene.tsx`

Tasks:

1. Define `OperationsChapterId`, `OperationsChapterState`, and `UrbanWorldFrame`
   from the approved design. Keep all values normalized and renderer-neutral.
2. Add `toOperationsChapterState(snapshot, selection, replay, simulation)` to
   map existing `OperationsSnapshot` data to chapter labels, source provenance,
   focus entities, active metrics, and scene layer intent.
3. Preserve `UrbanFieldState.spatial` as the future cells/nodes/flows/zones
   extension point. Do not add production H3 or new API fields.
4. Add focused tests for chapter ordering, unavailable/degraded source states,
   selection mapping, bounded progress, and deterministic demo values.

Verification: unit tests and typecheck pass before layout migration starts.

## Phase 2: Replace the Operations Visual DOM

Files:

- `apps/web/src/App.tsx`
- `apps/web/src/components/OperationsExperience.tsx` (new)
- `apps/web/src/components/OperationsChapter.tsx` (new)
- `apps/web/src/components/OperationsNavigationRail.tsx` (new)
- `apps/web/src/components/OperationsUtilityBar.tsx` (new)
- `apps/web/src/components/OperationsControlDock.tsx` (new)

Tasks:

1. Extract the current `OperationsView` content into `OperationsExperience`.
   Keep all existing command callbacks and state ownership in the route boundary.
2. Create seven semantic chapter elements in fixed content order. Each chapter
   gets a stable id, heading, focus label, source status, and slot for capability
   content.
3. Move the large Operations sidebar treatment behind an Operations-only compact
   rail. Keep `AppShell` behavior and all other role routes unchanged.
4. Move source mode, filters, health, simulation/replay commands, and refresh
   actions into the utility bar or chapter control dock without changing native
   controls, labels, callbacks, or keyboard order.
5. Keep an accessible content path for every capability even when its visual
   slot is overlapped or visually receded.

Verification: existing Operations unit/e2e behavior still finds source mode,
filters, controls, map, queue, lifecycle, and activity by their current labels.

## Phase 3: Build Distinct Chapter Compositions

Files:

- `apps/web/src/styles.css`
- `apps/web/src/components/OperationsChapter.tsx`
- `apps/web/src/components/ChapterInstrumentation.tsx` (new)
- `apps/web/src/components/OperationsControlDock.tsx`

Tasks:

1. Implement chapter-specific layout metadata rather than a shared viewport
   template. At minimum, define different dominant anchor, axis, scene role,
   typography alignment, instrumentation mode, and layer depth for all seven
   chapters.
2. Build Overview as a central/right-weighted world with large left typography
   and minimal instrumentation.
3. Build Urban Pressure as a left-shifted close field with right-side floating
   metrics and an overlapping heatmap.
4. Build SLA/Risk as a risk-first composition with an enlarged foreground trend
   and hotspot alignment into the world.
5. Build Strategy as a diagonal scene-to-instrument wall hand-off with strategy
   surfaces floating at different depths.
6. Build Live Operations as an inspection bay with a shallow world, enlarged
   route/map foreground, tall queue rail, horizontal lifecycle track, and event
   stream.
7. Build Simulation/Replay as a time-axis composition with a bottom control dock
   and replay/simulation state in the persistent world.
8. Build Research/Reliability as a spacious evidence wall with stable camera and
   localized evidence focus.
9. Use asymmetric grids, overlap, large negative space, partial off-screen
   nonessential visual elements, and foreground/middle/background layering. Do
   not use the existing card grid as the chapter skeleton.
10. Keep text, metrics, charts, and controls in readable DOM layers above or
    beside visual overlaps.

Verification: browser static screenshot with motion disabled must show seven
distinct composition contracts, not seven copies of one template.

## Phase 4: Persist and Reframe the Three.js World

Files:

- `apps/web/src/components/PersistentUrbanWorld.tsx` (new)
- `apps/web/src/components/UrbanFieldScene.tsx`
- `apps/web/src/components/UrbanFieldFallback.tsx`
- `apps/web/src/components/OperationsMotionCoordinator.tsx`

Tasks:

1. Mount `UrbanFieldScene` exactly once inside `PersistentUrbanWorld`, outside
   chapter elements that change focus or layout.
2. Replace the current progress-only scene inputs with `UrbanWorldFrame`.
3. Add camera modes for wide overview, close pressure, risk hotspot, strategy
   pullback, live inspection, replay tracking, and stable research framing.
4. Map chapter layer visibility to cells, flows, risk zones, nodes, and core.
5. Map chapter lighting to key, ambient, and risk signals without drifting into
   neon/cyberpunk styling.
6. Preserve DPR cap, resize, visibility pause, reduced-motion behavior, WebGL
   fallback, composer disposal, and no-duplicate-context invariant.
7. Ensure the fallback renders the same chapter composition and semantic state,
   rather than reverting to the old Hero summary layout.

Verification: scene mount count is one across the entire chapter track; canvas
pixels remain nonblank; route changes dispose the context; fallback remains
accessible.

## Phase 5: Recompose Analytical Surfaces

Files:

- `apps/web/src/components/ChapterInstrumentation.tsx`
- `apps/web/src/components/AnalyticalVisualizationFoundation.tsx`
- `apps/web/src/styles.css`

Tasks:

1. Preserve existing SVG chart primitives, labels, tooltip titles, thresholds,
   legends, and keyboard focus.
2. Add `hero`, `floating`, `edge`, and `docked` display modes.
3. Move throughput, SLA/risk, latency/throughput, strategy distribution, and
   heatmap into chapter slots rather than a repeated chart-card strip.
4. Allow the risk chart to occupy a foreground layer, the pressure heatmap to
   overlap the scene, and strategy distribution to form an offset instrumentation
   wall.
5. Keep chart values and provenance sourced from existing snapshot/demo state.
6. Ensure chart containers do not transform critical labels, axes, or controls.

Verification: chart tests pass; all five representative analytical surfaces are
reachable by keyboard and remain readable with motion disabled.

## Phase 6: Unify Scroll and Semantic Pointer Inspection

Files:

- `apps/web/src/components/OperationsMotionCoordinator.tsx`
- `apps/web/src/components/OperationsExperience.tsx`
- `apps/web/src/components/UrbanFieldScene.tsx`
- `apps/web/src/components/ChapterInstrumentation.tsx`

Tasks:

1. Scope one GSAP/ScrollTrigger context to `OperationsExperience` and one RAF
   frame sampler to the persistent chapter track.
2. Publish active chapter, local progress, velocity, camera mode, scene role,
   instrumentation mode, and focus strength to DOM and scene controller.
3. Classify pointer targets as scene cell/route/risk-zone/core, chart region,
   HUD, or control. Controls disable lens distortion.
4. Feed the same pointer frame to camera parallax, local scene inspection,
   chart region focus, HUD readout, and bounded lens pass.
5. Keep RGB shift at zero at rest and cap it to a short transient response.
6. Add semantic focus transitions only at chapter thresholds; avoid per-frame
   React renders.
7. Revert all ScrollTrigger timelines and listeners on unmount or route change.

Verification: pointer target and chapter frame tests pass; browser inspection
shows semantic focus rather than decorative cursor movement.

## Phase 7: Responsive, Reduced-Motion, and Capability States

Files:

- `apps/web/src/styles.css`
- `apps/web/src/components/OperationsExperience.tsx`
- `apps/web/src/components/UrbanFieldFallback.tsx`

Tasks:

1. Define independent desktop, laptop, and mobile chapter compositions.
2. On desktop, permit asymmetric overlap and persistent sticky world.
3. On laptop, reduce scene detail and collapse the rail while preserving depth.
4. On mobile, use chapter-local flow and bottom control dock; disable pointer
   lens overlay for coarse input and prevent horizontal overflow.
5. In reduced-motion mode, preserve all seven redesigned static compositions;
   disable camera drift, deformation, route flow, lens chromatic shift, and large
   interpolated transitions.
6. Keep loading, degraded, unavailable, demo, replay, and simulation states
   explicit in every affected chapter.

Verification: 1280x720, 1024x768, and 760x800 screenshots show no overlap that
harms content, no horizontal overflow, and usable controls.

## Phase 8: Test and Browser Visual Quality Gate

Files:

- `apps/web/src/components/OperationsExperience.test.tsx` (new)
- `apps/web/src/components/OperationsMotionCoordinator.test.tsx` (new)
- existing Operations and visual tests
- `evidence/gates/RM-240/operations-immersive-world.md` (new)

Automated checks:

1. `npm run format:check`
2. `npm run lint`
3. `npm run typecheck`
4. `npm run test:unit`
5. `npm run build`
6. targeted and full Playwright suites;
7. control-plane validation.

Browser checks:

1. Select deterministic Demo mode.
2. Capture each chapter entry and hand-off at desktop, laptop, and mobile sizes.
3. Perform one uninterrupted normal-wheel/trackpad scroll from top to bottom.
4. Observe whether the scene persists and changes role across all chapters.
5. Move pointer across scene cells, routes, risk zones, core, charts, HUD, and
   controls; verify semantic inspection and bounded transient RGB response.
6. Repeat with reduced motion and judge the static composition independently.
7. Disable animation in-browser and confirm the route no longer resembles the
   old dashboard even when frozen.
8. Record console logs, canvas pixels, scene mount count, scroll width, and any
   visual fatigue or hand-off discontinuity.

The gate fails if any two chapters look like the same template, if later detail
sections return to conventional card grids, if the scene disappears between
chapters, or if controls/readability degrade.

## Phase 9: Evidence, Task Graph, and Checkpoint

Files:

- `evidence/gates/RM-240/operations-immersive-world.md`
- `TASK_GRAPH.yaml`
- `PROGRESS.md`
- `HANDOFF.md`

Tasks:

1. Record executable test results and browser observations without claiming
   production telemetry or external provider validation.
2. Add RM-240 only after executable evidence exists; status `passed` requires
   automated and browser visual gates, not code existence.
3. Preserve unrelated PR-001, PR-007, `.codex-tmp/`, and `.superpowers/` changes.
4. Commit the implementation as a coherent standalone checkpoint. Push only if
   explicitly requested; otherwise leave the local commit ready for review.

## Risk Controls

- If the chapter track becomes too tall or tiring, reduce per-chapter dwell
  while preserving the distinct composition contract; do not revert to cards.
- If GSAP or ScrollTrigger fails to initialize, use the native progress fallback
  while keeping the redesigned chapter DOM and static layout.
- If mobile overlap harms readability, move the visual layer behind the content
  and retain chapter-specific typography/instrumentation rather than applying a
  desktop grid wholesale.
- If Three.js performance drops, reduce instanced detail and post-processing
  before removing the persistent-world role.
- If an existing capability component cannot fit a chapter slot, wrap or split
  its presentation at the Operations boundary; do not alter its business data
  or command contract.
