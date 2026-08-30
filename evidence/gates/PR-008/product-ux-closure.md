# PR-008 Product UX Closure Evidence

Date: 2026-08-30

Status: `VALIDATING_REMOTE_CI`

## Scope

This checkpoint closes the bounded Product Readiness UX task without expanding
the separately approved Immersive Operations campaign. It does not change API
ownership, business-state authority, Digital Twin claims, Round 4 progress, or
scientific results.

## Audit and implementation

- Operations, Strategy Lab, Customer, Merchant, and Courier remain inside one
  product shell with consistent source selection, identity boundary, service
  status, freshness, and availability language.
- Live mode fails closed without a verified OIDC session. Demo mode is labeled
  as an isolated non-production fixture and never substitutes silently for live
  data.
- Loading, empty, error, degraded, stale, unavailable, reconnecting, and command
  failure states retain focused unit/browser coverage. Demo and replay write
  controls are disabled with an explicit reason.
- The Operations route intentionally uses a compact icon rail. Each icon now has
  a visible hover/focus label plus matching `title`, `data-label`, and ARIA name;
  the mobile drawer continues to show the full route labels.
- No decorative-only rewrite, external provider operation, paid dependency, or
  backend contract change was introduced.

## Operator walkthrough

The local app was inspected in the in-app browser at desktop `1440x900` and
mobile `390x844` viewports:

- Operations rendered a nonblank persistent urban world, all seven chapters,
  explicit demo provenance, usable source controls, and the new compact-nav
  hover label.
- Strategy Lab exposed recorded-vs-unavailable distinctions, runnable local
  comparison controls, lineage boundaries, and no fabricated strategy ranking.
- Customer, Merchant, and Courier presented their primary lifecycle actions in
  one consistent shell; demo writes stayed disabled with an on-screen reason.
- The mobile Operations world, navigation drawer, Strategy Lab, and Courier
  action layout remained readable with no horizontal overflow. The drawer
  exposed all five routes and retained focus-visible styling.
- Browser console inspection returned zero warnings or errors during the final
  walkthrough.

## Executable gates

- `npx prettier --check src e2e package.json playwright.config.ts vite.config.ts`:
  passed. The repository-wide package wrapper cannot traverse the pre-existing
  ignored `apps/web/playwright-report/data` Windows ACL, so tracked web inputs
  were checked directly.
- `npm run lint`: passed.
- `npm run typecheck`: passed.
- `npm run test:unit`: 40 test files and 112 tests passed.
- `npm run build`: passed. Vite retained its existing advisory for chunks over
  500 kB; no build failure occurred.
- `npm run test:e2e -- --reporter=line`: 36 passed, 2 device-conditional tests
  skipped, 0 failed across desktop and mobile projects.
- The browser suite includes primary-route rendering, mobile overflow, keyboard
  reachability, focus containment/return, loading/unavailable, stale state,
  backend reconnect and event deduplication, simulation errors, and Axe scans on
  every primary route.

## Claim boundary

- External operations: `NONE`.
- External cost: `USD 0.00`.
- Round 4 progress changed: `NO`.
- Scientific claims changed: `NO`.
- Final task status remains `validating` until the normal non-force publication
  is green in GitHub Actions.
