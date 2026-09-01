# RM-251 Visual Material System Recomposition

## Decision

Adopt prototype A, **Frosted Atlas**: a dark, geographically readable city map
surrounded by a cool graphite / silver-blue atmosphere, with light frosted glass
instrumentation floating above the map. This preserves the operational depth of
RouteMind while removing the uninterrupted dark-green/cyan dashboard tone.

The redesign is a presentation-layer checkpoint. City switching, MapLibre and
Deck.gl contracts, courier density/LOD, Pointer Square Lens, replay semantics,
research evidence semantics, and bilingual behavior remain unchanged.

## Visual system

The page gains explicit material tokens in the existing CSS system:

- Environment: graphite base, cool slate, silver-blue atmospheric fields, and
  chapter-level focal lighting. The map remains dark enough for road and route
  contrast.
- Glass: translucent light surfaces with backdrop blur, saturation, inner
  highlight, soft ambient shadow, and a low-contrast border only where separation
  is semantically needed.
- Semantic accents: demand uses muted blue, supply uses restrained mint, risk
  uses amber/red, strategy uses desaturated violet-blue, and brand activity uses
  a controlled teal. No single cyan accent is reused for every state.
- Radius: large floating surfaces use a soft 20-24px radius, compact controls
  use 10-14px, and technical evidence/table surfaces remain 6-8px.
- Typography: narrative headings keep editorial scale; operational labels use
  sentence case by default, reserving uppercase mono labels for provenance,
  source, and machine identifiers.

The material primitives are CSS/React semantics rather than a new component
framework: `glass-surface`, `glass-overlay`, `glass-rail`, `glass-dock`,
`glass-inspector`, and `glass-metric`. Existing components opt into a primitive
according to their role. A metric may remain free typography or inline
instrumentation when a box would weaken the composition.

## Composition and light choreography

Operations uses the persistent map as the dark anchor. A low-frequency radial
light field follows the selected city/focus and changes gently between chapters:

- Overview: dark map with the lightest editorial copy zone and a silver-blue
  halo around the active city.
- Urban pressure: cool translucent atmosphere and more visible supply/demand
  instrumentation.
- SLA/risk: slightly warmer focal light; amber/red appears only on risk signals.
- Strategy: neutral frosted analysis surfaces with restrained violet-blue
  strategy markers.
- Live detail: darker map framing with floating inspectors and clear route
  hierarchy.
- Replay: softer graphite/fog field around the timeline.
- Research: lighter evidence treatment while preserving the dark spatial anchor.

These are tonal shifts within one token system, not seven unrelated themes.
City identity is a small ambient modifier: Shanghai adds a cool blue-gray with a
restrained warm metropolitan highlight, Shenzhen a cleaner cyan-blue linear bias,
and Chengdu a softer slate field with a small amber undertone.

## Interaction and motion

The existing GSAP chapter coordinator remains the owner of scroll choreography.
Material response is an additional layer:

- chapter handoff adjusts atmospheric focal point, glass opacity, blur strength,
  and depth in a short eased transition;
- the focused inspector sharpens while surrounding overlays soften;
- background drift is nearly imperceptible and disabled under reduced motion;
- Pointer Square Lens remains the geographic inspection interaction and can affect
  local map clarity/refraction, but does not distort critical controls or text;
- no global bloom, persistent rainbow fringe, bouncing cards, or decorative glow.

Reduced-motion mode keeps the full composition, map, glass hierarchy, and static
gradients. It freezes gradient drift, blur interpolation, chromatic motion, and
nonessential material animation; it does not replace the map with a fallback.

## Implementation boundaries

1. Add shared visual tokens and material utility classes to the existing web CSS.
2. Add a small React/CSS material wrapper only where it removes repeated class
   logic; do not introduce a new design-system package.
3. Update `AppShell`, `OperationsExperience`, analytical panels, strategy/research
   surfaces, and detail inspectors to use the primitives selectively.
4. Preserve the existing MapLibre basemap-provider boundary and Deck.gl layers.
5. Preserve the existing `useLocale` contract and localize any new visible text.
6. Do not modify backend services, map data contracts, courier generation, or
   production-provider credentials.

## Responsive and accessibility behavior

At 1280x720, the map remains the dominant dark anchor and floating glass surfaces
retain readable spacing. At 1024x768, secondary overlays reduce opacity and move
to a single clear rail. At 760x800, surfaces become more opaque, overlap is
reduced, and technical data stacks vertically without horizontal overflow.

Glass foreground text must meet the existing contrast expectations. Busy map
regions receive higher glass opacity rather than lower text contrast. Focus rings,
native cursor behavior, keyboard access, and color-independent status labels are
preserved.

## Verification gates

- Static gate: disable animation and verify the page no longer reads as a
  dark-green AI dashboard with repeated bordered cards.
- Material gate: inspect transparency, blur, inner highlight, shadow, and tonal
  hierarchy in real browser rendering; reject `rgba(0,0,0,0.4) + border + blur`
  as the sole treatment.
- Browser gate: inspect 1280x720, 1024x768, and 760x800 in Chinese and English;
  capture before/after and static-motion-disabled evidence.
- Functional gate: city switching, pointer lens exclusion, courier LOD, selected
  courier flow, replay, research evidence, and language switching remain intact.
- Automated gate: existing format, lint, typecheck, unit, build, and relevant
  browser smoke tests must pass.

## Self-review

- Scope is limited to visual materials, composition, and motion response.
- The selected prototype is explicit and consistent with the user's A choice.
- Map readability and all operational/data contracts remain protected.
- Reduced motion keeps WebGL/map availability and only freezes nonessential motion.
- No credentials, provider migration, backend work, or unrelated refactor is
  introduced.
- Every new visible label has a bilingual path through the existing locale layer.
