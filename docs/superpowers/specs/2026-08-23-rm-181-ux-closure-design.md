# RM-181 UX, Accessibility, and Mobile Closure Design

## Goal

Close the browser quality gate around the existing role-aware surface without
changing the source-of-truth boundary. The work is limited to interaction
semantics, visible state communication, keyboard focus behavior, and executable
browser evidence across desktop and mobile.

## Acceptance evidence

The Playwright gate must cover:

1. Live loading and unavailable states, including the source detail exposed to
   the user and an axe scan of the unavailable surface.
2. Live degraded courier freshness and realtime stale state, including the
   recovery/refresh affordance and an axe scan of the degraded surface.
3. Simulation control error feedback and successful form control, replay event
   inspection, and strategy/what-if comparison controls.
4. Mobile navigation focus: opening moves focus into the navigation, Tab and
   Shift+Tab remain inside it, Escape closes it, and focus returns to the menu
   toggle. The existing viewport overflow and role-route checks remain.
5. Map order markers and strategy metric rows expose meaningful accessible
   names instead of relying on color or decorative geometry.

## Implementation boundaries

- React remains a presentation and command-surface client; Java/Python APIs
  remain authoritative for durable state and dispatch/simulation correctness.
- No fake button is added. Existing navigation/health controls remain usable;
  the closure focuses on controls already backed by source or test fixtures.
- Tests use deterministic Playwright route fixtures and do not claim live
  production availability, map-provider coverage, or device-lab certification.
- Existing visual language and responsive layout are preserved; changes use
  stable dimensions and the current component/CSS conventions.
