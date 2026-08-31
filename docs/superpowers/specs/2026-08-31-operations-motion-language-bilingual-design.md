# RM-250 Operations Motion Language and Bilingual UI

## Context and audit

The existing Operations route already owns one persistent MapLibre + Deck.gl
world, a seven-chapter controller, GSAP/ScrollTrigger coordination, the full
OpenFreeMap Liberty style, deterministic Option B courier density, and the
Codrops-derived optical map lens. The browser audit at 1280px showed that the
world is visually credible, but the later Operations content still reads as a
collection of independent panels. Repeated heading/value/subtitle cells and the
large `Data-backed flow visualization` surface interrupt the spatial narrative.
All shell and Operations copy is currently hard-coded English, while the
preferences domain only stores a locale value and does not drive rendering.

## Chosen approach

Extend the existing React architecture with a small typed locale runtime and a
tokenized motion vocabulary. A new general chart library is unnecessary: the
existing SVG analytical foundation is deterministic, accessible, and already
shares the graphite/teal/amber/red tokens with the map. It will be composed as
chapter instrumentation rather than rendered as generic dashboard cards.

The locale runtime exposes `LocaleProvider`, `useLocale`, `t`, and Intl-backed
number/date/relative helpers. It supports `zh-CN` and `en-US`, chooses a safe
browser default, persists to a local key, switches without reload, and falls
back to English for missing keys. Technical identifiers (RADS, VRPTW, P50/P95/
P99, H3, SLA, strategy IDs) remain unchanged.

The motion vocabulary exposes named roles for reveal, relocate, focus, handoff,
inspect, chapter transition, map camera, and analytical emphasis. Existing
ScrollTrigger frames continue to own native scroll progress; CSS variables and
chapter-specific composition rules express the state. Reduced motion freezes
continuous drift, parallax and chromatic response while retaining the spatial
composition and WebGL scene.

## Chapter composition contract

1. Network Overview: map/network dominant, sparse copy, oversized signal readout.
2. Urban Pressure: map shifts into the background while the spatial heatmap
   occupies a diagonal foreground field.
3. SLA/Risk: risk trend and exception annotation become the foreground; map
   remains a contextual hotspot layer.
4. Strategy: comparison becomes a directional decision lane with migration
   emphasis instead of a static bar-card grid.
5. Live Operations: one inspection composition combines map, flow evidence,
   selected entity and activity; old metric-card repetition is de-emphasized.
6. Simulation/Replay: the time axis is the primary visual anchor and controls
   choreograph the persistent world.
7. Reliability/Research: a quiet evidence wall with provenance and invariant
   hierarchy closes the environment.

The `Data-backed flow visualization` remains available for inspection, but it is
styled as an edge-instrumentation layer in Live Operations, with the persistent
map and selected handoff carrying primary hierarchy. No production telemetry or
new Digital Twin claim is introduced.

## Implementation boundaries

- Preserve MapLibre + Deck.gl, the basemap provider boundary, Option B population
  (Shanghai 120/32, Shenzhen 90/26, Chengdu 104/28), and the pointer lens.
- Keep animation and pointer sampling in refs/render-loop state; locale changes
  are ordinary React updates and never run per animation frame.
- Keep every chapter in the existing DOM order and use native scrolling. GSAP is
  limited to composition hand-off and focus choreography already coordinated by
  `OperationsMotionCoordinator`.
- Localize visible Operations shell, chapter, map/HUD, chart, flow, replay,
  reliability, control, loading, error, and accessibility copy. Data values and
  backend identifiers stay data-driven.

## Verification and visual gates

- Unit tests cover locale default, switch, persistence, fallback, key rendering,
  Intl number/date interpolation, and chapter composition metadata.
- Browser gates cover static no-motion composition, enabled motion hand-offs,
  Chinese and English at 1280x720, 1024x768, and 760x800, continuous top-to-
  bottom scroll, pointer lens response, and zero overflow/console errors.
- Evidence records before/after screenshots and notes the intentional difference
  from Codrops media demos: RouteMind refracts a live geographic composition
  rather than a static image, while preserving their spatial pacing, lens,
  parallax, and role-transition techniques.

## Self-review

- No unresolved placeholders or scope expansion into Presentation Mode, a
  national globe, full Digital Twin, or Decision X-Ray implementation.
- Existing renderer-neutral contracts remain the source of scene state; the
  locale runtime does not enter the WebGL lifecycle.
- The approach is compatible with the current dependency set and introduces no
  new paid provider, API key, or general-purpose chart dependency.
