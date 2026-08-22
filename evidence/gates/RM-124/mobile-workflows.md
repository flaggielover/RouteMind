# RM-124 Mobile Role Workflow Experience

Date: 2026-08-22

## Implemented contract

- Mobile uses an explicit workspace navigation drawer instead of requiring a
  horizontal role-nav swipe. The drawer exposes all five routes, has 44px role
  links, closes after navigation, and closes on Escape while preserving focusable
  semantic controls.
- Customer, merchant, and courier command surfaces keep their real command
  boundaries and remain reachable at mobile widths. Touch actions use stable
  mobile sizing and courier actions use a two-column layout with a full-width
  location action on narrow screens.
- Demo and replay remain explicitly read-only; mobile layout changes do not turn
  fixture actions into fake writes.

## Evidence

- Web static/unit gate passes with 38 tests and a production build.
- Playwright browser gate passes 17 tests with one desktop-only skip. The mobile
  project passes role-route rendering, no-overflow, navigation-drawer role-action
  reachability, and axe accessibility coverage for all five roles.
- The mobile screenshot `apps/web/test-results/operations-mobile.png` shows the
  drawer and responsive operations surface at the iPhone 13 viewport.
- Full repository gate passes with Java 60 tests, Python 59 tests at 96.13%
  coverage, and 5 schemas/15 contract fixtures.

## Gate decision

Local L4 mobile workflow and accessibility evidence is complete. Remote Actions
run `32575052384` passed all five jobs, including the Web static/unit and browser
smoke gates. RM-124 is fully validated.
