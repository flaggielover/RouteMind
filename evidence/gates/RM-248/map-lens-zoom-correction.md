# RM-248 Map Lens and Zoom Correction

Date: 2026-08-31

## Scope

This correction responds to the Operations visual review:

- reduce the existing Codrops-style square optical lens to one fifth of its
  previous effective size;
- restore usable MapLibre zoom controls without trapping the page scroll.

## Implementation

- `resolveMapOpticalLensTarget` now uses a 5.8% short-edge lens with a compact
  34-48px CSS clamp. The existing WebGL CC Lens displacement and velocity RGB
  response remain unchanged.
- MapLibre uses cooperative gestures: plain wheel input continues page scroll,
  while Ctrl/Cmd + wheel zooms the map. The existing Zoom in and Zoom out
  controls remain available for direct operation.
- The map exposes its current zoom as `data-map-zoom` for browser observability.
- The cartographic legend is presentation-only and no longer intercepts the
  bottom-left MapLibre controls.

## Browser Evidence

On `http://127.0.0.1:4175/operations` at the desktop viewport:

- the optical square is materially smaller and remains pointer-following;
- MapLibre Zoom in changes the Shanghai camera from `11.13` to `12.13`;
- Zoom out restores `11.13`;
- the page remains continuously scrollable over the map surface;
- the native cursor and UI exclusion behavior remain unchanged.

## Automated Evidence

- focused unit tests: map lens target and PersistentGeoWorld pass;
- focused Playwright premium geographic test passes, including zoom in/out,
  lens response, reduced motion, city switching, and page scroll;
- format, typecheck, and lint pass.

The map and courier field remain deterministic Demo/Synthetic visualization;
this change introduces no production telemetry or provider claim.
