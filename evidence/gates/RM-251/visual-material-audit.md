# RM-251 Visual Material Audit

Date: 2026-09-02

## Browser evidence

- Primary inspection URL: `http://localhost:52452/operations` (current workspace Vite instance).
- Data mode: DEMO / synthetic snapshot.
- Desktop viewport: in-app browser, 1280x720 capture.
- Browser checks covered the initial map overview and continuous scroll through
  pressure, SLA/risk, strategy, live detail, replay transition, and research
  surfaces. City map, route layers, HUD, chapter rail, and analytical surfaces
  remained present as one persistent composition.
- A 390x844 Chromium viewport capture was also taken to verify the responsive
  shell. Narrow rules increase surface opacity, reduce overlap, and preserve
  readable controls; the page has no horizontal overflow in the existing mobile
  gate.

## Visual observations

- Overview retains the dark, detailed vector map as the spatial anchor while the
  surrounding field shifts to graphite and silver-blue rather than uninterrupted
  green/cyan.
- Pressure uses a cool translucent analytical surface; SLA/risk introduces a
  warmer, localized risk field; strategy shifts to a desaturated violet-blue
  surface. These are tonal hand-offs, not separate page themes.
- Glass roles are visibly differentiated: rail, overlay, analytical surface,
  chart metric, inspector, and replay dock use different opacity, blur, radius,
  and shadow levels. Technical data stays more opaque for legibility.
- The map remains readable under the new atmosphere. Pointer Lens and map
  controls stay in the geographic layer; UI controls are not globally distorted.
- No global bloom, persistent rainbow fringe, decorative custom cursor, or
  generic neon/cyberpunk treatment was introduced.

## Reduced motion

The existing motion coordinator keeps the WebGL/MapLibre world available when
`prefers-reduced-motion` is enabled. Automated browser coverage confirms the
seven chapter composition remains present, the persistent world remains mounted,
and the mobile layout stays within the viewport. CSS material transitions are
disabled in reduced-motion mode while static atmosphere and hierarchy remain.

## Automated gate evidence

- `npm run typecheck` passed.
- `npm run lint` passed.
- `npm run test:unit` passed: 47 files, 133 tests.
- `npm run build` passed.
- `npx playwright test locale.spec.ts --reporter=line` passed: 3 passed, 1
  expected mobile skip.
- `npx playwright test web.spec.ts -g "keeps the mobile layout" --project=mobile --reporter=line` passed.

The first Playwright run with the repository HTML reporter also passed its three
executed tests but returned an EPERM while creating `playwright-report`; the
text-reporter rerun is the authoritative clean result.
