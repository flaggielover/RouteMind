# RM-229 What-if Delta Visualization Evidence

Date: 2026-08-24  
Status: passed

## Scope

- Added a pure What-if delta projection against the recorded `baseline` result.
- The panel shows coverage objective delta, duration delta, risk delta, and
  changed/unchanged status for each bounded variant.
- Run identity, baseline/variant replay digests, and output digest remain
  visible as source decision evidence.
- The objective is coverage (`assignment_rate`) only; no combined production
  score or causal inference is introduced.

## Local evidence

- `./scripts/web.ps1 check`: PASS - 32 test files, 88 unit tests, Prettier,
  ESLint, TypeScript, and Vite production build.
- `./scripts/web.ps1 e2e`: PASS - 34 Playwright tests, 2 existing desktop-only
  skips. Strategy What-if flow passes on desktop and mobile, including existing
  accessibility smoke coverage.
- Focused projection tests cover changed deltas, unchanged variants, missing
  baseline, and provenance links.

## Remote evidence

Checkpoint: pending

GitHub Actions: pending checkpoint push.

## Boundaries

Compute remains the source of bounded scenario variants and replay digests. Web
only projects deltas and never treats them as causal or production truth.
