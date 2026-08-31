# RM-250 Operations Motion Language + Bilingual UI Evidence

Date: 2026-09-01
Status: PASSED / LOCAL VISUAL CHECKPOINT

## Scope

Operations was audited as a persistent spatial environment rather than a set of
dashboard cards. The implementation keeps the React 19 + MapLibre + Deck.gl
boundary, the OpenFreeMap Liberty provider, Option B deterministic density, the
Codrops-derived square optical lens, and the existing analytical SVG foundation.
No production telemetry, paid map credential, Google SDK, H3 production feed,
or calibrated Digital Twin claim is introduced.

## Visual decision record

- Keep: persistent MapLibre/Deck.gl world, seven-chapter controller, analytical
  chart foundation, route/LOD semantics, pointer lens, and reduced-motion
  capability handling.
- Recompose: Overview, Pressure, Risk, Strategy, Live, Replay, and Research
  each use a different primary composition, depth emphasis, HUD hierarchy, and
  analytical role. Live evidence is a full-width inspection sequence and no
  longer collapses into the former 12-column narrow stack.
- Integrate: typed motion roles (`reveal`, `relocate`, `focus`, `handoff`,
  `inspect`, `chapter`, `mapCamera`, `analytical`) are shared by the scroll
  coordinator and CSS composition tokens. The locale runtime is React-context
  scoped and never participates in the render loop.
- Remove from primary hierarchy: repeated metric-card framing and generic
  dashboard spacing. Existing detailed operational controls remain available in
  the Live inspection sequence.

## Codrops adaptation

The visual language adapts Codrops spatial recomposition, camera/parallax easing,
analytical focus hand-off, and the square pointer-lens optical behavior to a
geographic operational frame. The map lens refracts MapLibre and Deck.gl content
in the same WebGL context, with transient velocity-sensitive chromatic sampling;
it intentionally differs from the media demo because the underlying surface is
interactive geographic data with UI exclusion zones.

## Browser evidence

Clean Playwright browser captures at 1280x720 (MapLibre status `ready`) are:

- `operations-en-overview.png`
- `operations-en-pressure.png`
- `operations-en-live.png`
- `operations-en-research.png`
- `operations-zh-overview.png`

The captures show real OpenFreeMap vector roads, waterways, district labels,
city-specific synthetic courier routes, and distinct chapter compositions. Live
is readable as a layered inspection surface; it does not render as a vertical
letter stack. Browser checks also covered narrow/mobile layout and reduced
motion. Reduced motion retains the WebGL/map composition while freezing
nonessential drift, pulses, route animation, and chromatic response.

## Automated gates

- Vitest: 47 files, 133 tests passed.
- TypeScript, ESLint, Prettier check, and production build passed.
- Focused locale/composition Playwright: desktop 2/2 passed; mobile 1 passed,
  1 intentional skip because the locale controls collapse behind the mobile
  navigation affordance.
- Existing Operations lifecycle and deterministic city-density Playwright:
  desktop 2/2 passed.
- `git diff --check` passed; no document or primary-panel horizontal overflow
  was observed in the browser gates.

## Provenance

All operational values in these captures are explicitly `DEMO / SYNTHETIC`.
The locale layer supports `zh-CN` and `en-US`, persists `routemind.locale`,
falls back safely to English, and formats numbers/dates through `Intl`.
