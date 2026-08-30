# RM-238 Frontend Visual Foundation Evidence

Date: 2026-08-30
Scope: `apps/web` only; existing React 19/Vite shell, backend contracts, and
PR-001 lifecycle files remain outside the ownership boundary.

## Implementation

- Native Three.js `0.180.0` is lazy-loaded by `UrbanFieldScene`.
- The scene maps `OperationsSnapshot` to `UrbanFieldState`, including optional
  spatial cells, nodes, flows, and risk zones for future H3/geohash adapters.
- WebGL lifecycle includes capped DPR, resize observation, visibility and
  viewport pause, reduced-motion freeze (WebGL remains available), disposal,
  and semantic static fallback on capability/init failure.
- Operations also renders a tokenized analytical strip with throughput, SLA/risk,
  latency/throughput, strategy distribution, and zone-pressure heatmap views.

## Automated gates

- `npx prettier --check src package.json package-lock.json`: PASS
- `npm run lint`: PASS
- `npm run typecheck`: PASS
- `npm run test:unit`: PASS, 39 files / 108 tests
- `npm run build`: PASS; Three.js scene is a separate lazy chunk. Vite reports
  the expected post-minification chunk-size advisory for the Three.js chunk.
- `npx playwright test --workers=4`: PASS, 34 passed / 2 existing skips.
  Coverage includes source modes, simulation/replay, keyboard reachability,
  mobile overflow, role routes, and Axe accessibility smoke.

The repository `npm run check` wrapper was also exercised. Its final rerun could
not expand an ignored Playwright report directory locked by the local browser;
the equivalent format, lint, typecheck, unit, and build commands above passed
with the generated report excluded from formatting traversal.

## Browser visual gate

Manual browser inspection used the local Vite server at
`http://127.0.0.1:4173/operations` with deterministic Demo data.

- Desktop: verified a nonblank WebGL canvas with perspective depth, instanced
  pressure columns, curved route ribbons, faceted/deforming intelligence core,
  node highlights, HUD/legend, and selective bloom.
- Narrow laptop (1024px): verified the hero rail remains adjacent to the scene,
  canvas resizes to its measured container, and document width stays within the
  viewport.
- Mobile (760px): verified hero rail and analytical charts stack, canvas remains
  visible at 678x329 device pixels, and document scroll width stays below the
  viewport width.
- Analytical view: verified five chart surfaces share graphite/slate framing,
  cool data accents, risk thresholding, focusable SVG points/cells, and explicit
  `Visual demo - non-production` provenance.
- Console review after the final scene patch showed no new Three.js geometry
  conversion warnings; historical warnings from earlier hot reloads were not
  reproduced.

The visual language adapts the spatial mechanisms described by the supplied
Codrops references without copying their branding, text, assets, or artwork.
No production telemetry, national globe, full Digital Twin, Presentation Mode,
Decision X-Ray redesign, or backend/API behavior is claimed by this checkpoint.
