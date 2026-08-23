# RM-181 Browser UX, Accessibility, and Mobile Closure

- Date: 2026-08-23 (Asia/Shanghai)
- Design: \`docs/superpowers/specs/2026-08-23-rm-181-ux-closure-design.md\`
- Implementation checkpoint: \`b61c8c2\`
- Gate decision: PASS
- Local browser command: \`npm run test:e2e\`

## Closure changes

- Mobile navigation now moves focus into the open navigation, traps Tab and
  Shift+Tab within its links, closes on Escape, and returns focus to the menu
  toggle. Existing route navigation still closes the drawer.
- Live loading, unavailable, degraded courier freshness, stale realtime cursor,
  simulation command errors, replay inspection, forms, map order markers, and
  strategy comparison states have deterministic browser coverage.
- Strategy metric bars expose group and metric names to assistive technology;
  the live realtime amber state now meets WCAG AA contrast on white.
- Decision details, queue filter reset, and local strategy registry controls
  perform inspectable actions. The environment settings icon was removed because
  it had no implemented behavior.
- Simulation command errors now render reliably under React StrictMode by
  resetting the mounted guard when the effect is established.

## Local evidence

- Playwright: 36 test instances, 34 passed and 2 skipped. The two skips are the
  existing desktop-only role-action test under the mobile project; no failure
  was suppressed.
- Desktop and mobile axe scans passed for all role routes and the live
  unavailable/degraded fixtures.
- The browser fixtures cover loading/unavailable HTTP 503, stale courier
  freshness, stale SSE cursor metadata, simulation HTTP 503 form error,
  keyboard focus containment, map marker focus, queue filter clearing, strategy
  registry expansion, and semantic strategy metric groups.
- \`./scripts/verify.ps1\` -> PASS.
- \`./scripts/full-gate.ps1\` -> PASS: Java 61 tests, Python 142 tests at 95.88%
  coverage, Web 49 unit tests and production build, five schemas/15 fixtures,
  and repository controls.

## Remote evidence

- GitHub Actions run \`32614866937\` initially failed in the Web job because the
  final App.tsx edit had not been formatted; no test failure was hidden.
- After formatting checkpoint \`b61c8c2\`, run \`32614952772\` passed all five jobs,
  including Web static/unit, Web browser smoke, Python, Java, bounded
  degradation, and control plane.

This is a deterministic local browser-quality closure and does not claim
device-lab certification, production traffic capacity, or external map-provider
availability.
