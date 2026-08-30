# RM-240 Immersive Operations World Evidence

## Scope and classification

- Validation time: 2026-08-30 20:38:44 +08:00.
- Base revision: `625d959`; this evidence is committed with the standalone RM-240
  checkpoint.
- Classification: local PRODUCT visual and interaction checkpoint over the
  existing deterministic Demo snapshot.
- No backend ownership, production telemetry, Digital Twin calibration, national
  globe, Decision X-Ray expansion, or Presentation Mode claim is introduced.

## Implemented boundary

- `OperationsExperience` owns seven chapters and one sticky
  `PersistentUrbanWorld`; the Three.js renderer mounts once and receives
  renderer-neutral `UrbanWorldFrame` state through `UrbanFieldSceneController`.
- `operationsChapterState` maps the existing `OperationsSnapshot` into chapter
  camera, lighting, layer, focus, instrumentation, and optional spatial
  cells/nodes/flows/zones contracts.
- The Intelligence Core uses faceted local deformation, asymmetric satellites,
  instanced pressure cells, route flows, node/risk-zone emphasis, physical
  materials, selective bloom, camera presets, and semantic pointer inspection.
- Overview, Pressure, Risk, Strategy, Live, Replay, and Research use distinct
  viewport compositions rather than one repeated panel template.
- Reduced motion keeps WebGL and freezes nonessential motion. Static frames use
  explicit resize/scroll/world-state redraws and a preserved drawing buffer;
  runtime preference changes stop and restart the RAF loop correctly.
- WebGL failure keeps the named static fallback and semantic metrics. The
  operations shell retains accessible navigation names at compact breakpoints.

## Browser visual gates

Browser: Codex in-app Chromium, Demo source, local Vite server at
`http://localhost:4173/operations`.

### Gate A - shell and persistent world

- One `.persistent-urban-world`, one `canvas.urban-field-canvas`, seven chapter
  sections, zero legacy `.operations-hero` nodes, and zero horizontal overflow.
- The old dashboard-first skeleton is replaced by a persistent left spatial world
  and a chapter track. The renderer remains mounted across all focus changes.

### Gate B - Overview, Pressure, and SLA/Risk

- Overview uses a centered network core and a large signal/readout composition.
- Pressure moves the camera close to the core/cell field and brings the spatial
  heatmap into a tilted analytical plane.
- Risk reframes the core partially off-screen around risk routes/zones and hands
  focus to the SLA trend and promise-boundary narrative.
- Normal motion and reduced motion were inspected. Reduced motion retained one
  WebGL canvas, used zero fallback nodes, and applied `transform: none` to the
  chapter.
- Reduced-motion WebGL pixel probe: 549 x 607 buffer, 58,371 colored pixels,
  32,950 bright pixels, mean max channel 27.9874, context not lost.

### Gate C - all seven frozen compositions

- With motion frozen, all seven compositions remain legible and immersive:
  Strategy uses a pullback plus edge instrumentation, Live becomes a geo
  inspection bay, Replay uses a temporal dock, and Research becomes an evidence
  wall with progressive disclosure.
- Desktop 1280 x 720, laptop 1024 x 768, and mobile 760 x 800 were inspected.
  Laptop tracks measured 389px world / 450px chapter; mobile used a 745px stage,
  one canvas, no lens, no overflow, and a working navigation drawer.
- Final mobile utility-bar check kept `Demo snapshot` visible with a 102px header,
  no overlap, and no horizontal overflow.

### Continuous scroll and pointer inspection

- Continuous 650px wheel steps traversed focus in this order:
  `overview -> pressure -> risk -> strategy -> live -> replay -> research`.
- Scroll reached 8,886px of a 9,606px document. Every sample retained exactly one
  canvas and zero horizontal overflow; no internal scroll trap or dashboard-style
  visual discontinuity appeared.
- Scene pointer inspection produced target `scene`, label `inspect field`, visible
  lens intensity, and `Focused entity intelligence-core`. Leaving the spatial
  root decayed target/intensity to `none`/zero; controls do not retain the lens.
- Browser console inspection returned zero warnings and zero errors.

## Reference comparison

- Interactive 3D Cluster: visible inheritance is in faceting, local deformation,
  material/light response, asymmetric satellite depth, pointer focus, and
  camera/parallax behavior. RouteMind geometry and data semantics are original.
- Wave Propagation Cube Grid: visible inheritance is in the instanced pressure
  field and local propagation model, adapted to future cells, flows, and zones.
- Cinematic 3D Scroll: visible inheritance is in eased camera targets, depth
  changes, pinned world continuity, and focus hand-offs. There is no scroll
  hijacking or Presentation Mode expansion.
- The result was rejected and corrected when reduced-motion WebGL rendered an
  empty static buffer; screenshots and canvas existence alone were not accepted.

## Automated gates

- `npm run format:check`: PASS.
- `npm run lint`: PASS.
- `npm run typecheck`: PASS.
- `npm run test:unit`: PASS, 40 files / 112 tests.
- `npm run build`: PASS, 1,882 modules; lazy `UrbanFieldScene` 542.66kB raw /
  136.96kB gzip; primary bundle 571.95kB raw / 174.60kB gzip.
- `npm run test:e2e -- --reporter=list`: PASS, 34 tests passed / 2
  device-conditional desktop tests skipped; desktop and mobile Axe smoke passed.
- `./scripts/resume.ps1`: PASS, including task-graph schema/dependency/state,
  tracked-secret isolation, dependency/workflow/IaC checks, and the fast
  repository gate.
- Playwright workers are capped at four because the suite now creates real WebGL
  contexts; this prevents GPU-context contention without weakening assertions.

## Visual artifacts

All files are under `evidence/gates/RM-240/screenshots/`.

- `desktop-overview.png` - SHA-256
  `f952e6a82a7f7b18513decdf23908bad993661d48f70c42b450c2082a2f84baf`.
- `desktop-pressure.png` - SHA-256
  `75ce5cac1c151cb64726e39ca1d65908fb818fc1845c578cc5e51327aafb662c`.
- `desktop-risk.png` - SHA-256
  `0ef597fffcfa8afe9e783ffe304995b7e22ae14a70f7595f92bb3e25d2fc10e2`.
- `desktop-strategy.png` - SHA-256
  `6a16d1d11876116e155ed3a477ed92bbe2014a1582f67875e4ee8a3874123f7f`.
- `desktop-live.png`, `desktop-replay.png`, and `desktop-research.png` record the
  restrained later operational chapters.
- `desktop-risk-reduced-motion.png` records the nonblank static WebGL state.
- `laptop-overview.png` and `mobile-overview.png` record responsive closure; final
  mobile SHA-256 is
  `9000190f7ec9ccd4a47dfa5e4e08ba2f386a5a2675defd581ef6f64ca225d078`.

## Residual constraints

- Spatial data remains deterministic snapshot-derived Phase 1 data, not H3 or
  production city telemetry.
- The lazy Three.js chunk is intentionally substantial. DPR is capped at 1.5,
  visibility pauses rendering, reduced motion becomes event-driven, and renderer
  disposal remains mandatory; future asset/shader growth must preserve this
  performance budget.
