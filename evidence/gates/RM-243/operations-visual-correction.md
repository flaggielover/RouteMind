# RM-243 Operations Visual Correction Evidence

## Scope

- Base revision: `3c2aa06`
- Date: 2026-08-31
- Classification: `PRODUCT`, excluded from Round 4 counts
- Target: focused correction of Operations spatial semantics, responsive content
  containment, and semantic pointer inspection

No production telemetry, H3 implementation, calibrated Digital Twin state, backend
ownership change, paid provider call, or production claim is introduced.

## Implemented correction

- Replaced the fixed 72-column visual grid with snapshot-derived district clusters.
  Each district owns a deterministic 17-cell hexagonal demand field and bounded risk,
  courier-supply, and selection metadata through the renderer-neutral spatial contract.
- Removed the large unexplained polyhedral cluster and orbital objects. A small
  faceted strategy anchor remains subordinate to district cells, distinct
  order/courier/merchant/risk nodes, directional route markers, and bounded SLA-risk
  surfaces.
- Added explicit in-scene grammar for districts, active flows, demand density,
  courier supply, route flow, SLA risk, and dispatch strategy.
- Removed the 156px global custom cursor/lens and its crosshair/label. Native cursor
  behavior remains; raycasting now identifies nodes, district risk surfaces, strategy
  anchor, and individual cells. Local lens energy is reduced and RGB shift is zero at
  rest, with only a bounded pressed inspection beat.
- Removed the Live Operations Multi-city/City-Zone overlap. City/Zone data uses a
  fixed compact table when space permits and a labelled row composition in narrower
  containers. Flow, reliability, analytics, lifecycle, and chapter compositions now
  reflow from their own available width.

## Browser visual gates

The in-app browser inspected the real local app at `http://localhost:4173/operations`
with Demo selected.

- `1280x720`: document overflow `0`; primary panel overflow list empty; City/Zone
  table overflow `0`; Multi-city and City/Zone overlap `0`.
- `1024x768`: document overflow `0`; primary panel overflow list empty; City/Zone
  overlap `0`; Strategy heading and analytical surface enter below the sticky header
  without clipping.
- `760x800`: document overflow `0`; primary panel overflow list empty; City/Zone
  panel/table overflow `0`; the first screen preserves the WebGL field before the
  narrative copy.
- Pointer: `.operations-pointer-lens` count `0`; moving over the strategy anchor set
  `data-pointer-target="scene"` and the visible context to
  `Inspecting dispatch strategy anchor`.
- Reduced motion: `data-motion-reduced="true"`, `data-scene-status="ready"`, canvas
  `549x607` CSS pixels, document overflow `0`, and a visible static spatial frame.
- Continuous scroll focus sequence:
  `overview -> pressure -> risk -> strategy -> live -> replay -> research`; document
  overflow remained `0` at every sampled hand-off.
- Console warnings/errors during browser gates: `0`.

Screenshots:

- `screenshots/desktop-overview.png`
- `screenshots/desktop-city-zone.png`
- `screenshots/laptop-strategy.png`
- `screenshots/narrow-overview.png`
- `screenshots/desktop-overview-reduced-motion.png`

## Automated gates

- `npm run check`: PASS
  - Prettier format check
  - ESLint
  - TypeScript project build
  - Vitest: 40 files, 112 tests
  - Vite production build
- `npx playwright test --workers=2 --reporter=list`: PASS, 36 passed and 2
  device-conditional skips
- Production assets: `UrbanFieldScene` 547.56 kB raw / 138.28 kB gzip; primary
  application bundle 573.96 kB raw / 175.48 kB gzip. The established lazy scene
  boundary remains intact; Vite's existing 500 kB advisory remains explicit.

## Result

RM-243 passes the focused visual correction gate. The persistent world now reads as
district demand, movement, supply, risk, and strategy state; the tested layouts do
not rely on accidental horizontal scrolling or overlapping fallback panels; and the
pointer behaves as semantic inspection rather than persistent decoration.
