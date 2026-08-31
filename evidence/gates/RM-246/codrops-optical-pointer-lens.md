# RM-246 Codrops Optical Pointer Lens Evidence

## Scope

- Base revision: `ef04f2b`
- Date: 2026-08-31
- Classification: `PRODUCT`, excluded from Round 4 counts
- Target: replace the RM-245 CSS inspection overlay with a recognizable adaptation
  of Codrops Pointer Square Lens Distortion over the persistent real-city map

OpenFreeMap/OpenMapTiles remains the geographic source. Courier paths, riders,
orders, pressure, flows, and risk remain deterministic `DEMO / SIMULATED` data.
This checkpoint introduces no production telemetry, route-provider validation,
H3 service, calibrated Digital Twin state, or scientific claim.

## Reference Study And Attribution

The primary visual and implementation references were opened and inspected before
and during implementation:

- Demo: <https://tympanus.net/Tutorials/PointerSquareLensDistortion/>
- Article: <https://tympanus.net/codrops/2026/08/25/building-a-mouse-following-square-lens-effect-with-three-js-and-glsl/>
- Linked source implementation: `tomoyukinakata/mouse-following-square-lens-effect`

The reference establishes a square sized at roughly `0.4` of viewport height,
CC Lens distortion `1.5`, radial channel offsets near `+0.01 / 0 / -0.01`, and
pointer interpolation near `0.1`. RouteMind uses the same core local-square UV,
CC Lens transform, radial per-channel sampling, and smooth-follow structure. The
upstream MIT notice is retained in `apps/web/THIRD_PARTY_NOTICES.md`; no branding,
copy, source media, or unique artwork was copied.

## Implementation

- Removed the `.geo-pointer-lens` DOM node, backdrop filtering, pseudo-element
  chromatic borders, CSS position variables, and coarse-pointer special case.
- Added one MapLibre custom WebGL2 layer after the interleaved Deck.gl overlay.
  It copies the already composited map framebuffer into one reusable GPU texture,
  then redraws only the square lens region.
- The fragment shader applies CC Lens radial displacement in local square UV,
  converts the displaced sample back into map texture coordinates, and samples
  red/green/blue independently along the local radial direction.
- The visible square is `0.39` of the smaller map dimension, clamped to 220-330 CSS
  pixels with a 2.5% corner radius. Distortion remains `1.5`; maximum RGB shift is
  `0.012` and is reached only under high pointer speed.
- Pointer position retains the existing `0.13` easing. Event velocity is sampled
  separately, normalized to frame velocity, attacked quickly for acceleration,
  and released over a short envelope. This avoids tying color separation to the
  slower lens position catch-up.
- Stable inactive or stationary frames do not request continuous MapLibre repaints.
  Resize reuses the same layer and reallocates only its capture texture.
- `onRemove` deletes the texture, buffer, vertex array, and program. Component
  cleanup explicitly removes the custom layer before finalizing Deck.gl and the
  MapLibre owner.
- Buttons, city controls, source provenance, map summary, selected-route panel,
  inspection text, legend, other HUD targets, forms, and chart targets deactivate
  the lens. No custom cursor was added.

## Intentional Geographic Adaptation

The Codrops demo uses a static editorial image and transforms the entire outside
surface with grayscale plus wave/noise. RouteMind leaves the outside map unchanged
because road hierarchy, SLA state, and operational color semantics must stay
readable. The adaptation also clips the effect to the geographic WebGL world,
keeps DOM controls above and undistorted, and disables RGB separation under
reduced motion. These are the only material visual differences; the square
following lens, local optical refraction, radial RGB split, smooth tracking, and
transient response remain directly recognizable.

## Browser Visual Gate

The Codrops demo and `http://127.0.0.1:4175/operations` were kept open in separate
in-app browser tabs and compared directly. The RouteMind tab was inspected after
each shader and velocity-envelope correction rather than only after tests passed.

- The lens is an immediately visible square optical region, not a circle, tooltip,
  glow, cursor replacement, outline, or simple scale magnifier.
- Basemap labels, water, road hierarchy, courier trajectories, rider markers,
  merchant/customer nodes, risk overlays, and selected-route emphasis are all
  refracted together because the layer samples the final map/Deck framebuffer.
- A fast acceleration probe measured a rendered RGB envelope peak of `0.00647`.
  Normal travel stayed near `0.001-0.003`; a 900 ms stationary sample returned to
  `0.00000` in the final probe. There is no permanent rainbow fringe.
- Hovering the map summary or city controls set `data-lens-active=false`; moving
  back onto geographic content restored the lens without a React render loop.
- Reduced motion retained one nonblank WebGL lens with distortion `1.50` and RGB
  shift exactly `0.00000`.
- Desktop 1280x720, laptop 1024x768, and narrow 760x800 all retained one canvas,
  zero old CSS lens nodes, zero horizontal document overflow, and readable UI.
- Fresh in-app and standalone browser passes contained no page errors, application
  console errors, or application warnings.

Representative local evidence:

- `screenshots/01-desktop-moving.png`
- `screenshots/02-desktop-rest.png`
- `screenshots/03-laptop-rest.png`
- `screenshots/04-narrow-rest.png`
- `screenshots/05-reduced-motion.png`

Visual verdict: **PASS**. The interaction is recognizable as a geographic
adaptation of the Codrops square optical lens rather than a custom semantic hover
effect that merely shares the idea.

## Automated And Repository Gates

- `npm run check`: PASS; Prettier, ESLint, TypeScript, 44 Vitest files / 122 tests,
  and Vite production build.
- Optical target and component lifecycle tests: PASS; CSS-to-framebuffer mapping,
  lens sizing, velocity RGB bounds, reduced motion, UI exclusion state, layer
  registration, and explicit removal are covered.
- `npx playwright test --reporter=list`: PASS; 37 passed / 3 intentional
  device-conditional skips. The geographic test verifies a single canvas, active
  WebGL lens mode, distortion, transient RGB, rest decay, HUD/control exclusion,
  runtime reduced-motion switching, city switching, and untrapped page scroll.
- `npm audit --omit=dev`: PASS; 0 vulnerabilities.
- `./scripts/verify.ps1`: PASS; task graph, repository integrity, security,
  research/control-plane contracts, Compose, and fast repository gates.

The existing Vite warning for the lazy MapLibre/Deck bundle over 500 kB remains.
The route stays lazy, and this checkpoint adds shaders only to that existing lazy
chunk rather than eagerly loading another renderer.

## Ownership Boundaries

Java durable business authority and Python optimization/simulation ownership are
unchanged. The lens is a renderer-only inspection surface over deterministic demo
state. It does not obtain dispatch authority or change source-of-truth semantics.
