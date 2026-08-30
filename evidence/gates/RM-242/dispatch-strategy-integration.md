# RM-242 Evidence

Checkpoint: `RM-242 — Dispatch Strategy Completion & Integration`

Scope: bounded engineering integration only. No paid/cloud provider, live
customer system, research selector, frozen scenario mutation, or scientific
claim was used.

Before-state matrix: `docs/product/DISPATCH_STRATEGY_CAPABILITY_MATRIX.md`
After-state execution contract: `docs/product/MULTI_STRATEGY_EXECUTION.md`

Implemented/completed:

- Added deterministic `local-search@1.0.0` with `max_iterations` 1..256,
  standard `DispatchDecision`, independent solver verification, and no global
  optimality claim.
- Preserved and enriched the seven existing registry strategies with explicit
  capabilities and versioned parameter descriptors.
- Added explicit bounded dynamic insertion and dynamic replanning capability
  paths with prior-plan, trigger, resulting-plan, provenance, and replay fields.
- Added fixed-strategy scenario comparison and CLI strategy selection. Separate
  comparisons do not manufacture policy switches.
- Propagated actual travel-provider fallback state into RM-237 observations.
  Historical RM-241 artifacts remain unchanged; AD-002 remains recorded as a
  historical measurement artifact.
- Made Strategy Lab selectors and registry panels API-driven with a bounded
  offline descriptor snapshot.

Focused evidence: eight dispatch-completion tests plus the existing replanning,
simulation, VRPTW, registry, API, and RM-241 compatibility suites pass. The
compute gate passes Ruff, format, mypy, contract validation, 963 Python tests,
95.02% coverage, determinism, analytics archive/mart, semantic metrics, and
solver verification. The Java boundary gate passes 167 Maven tests. The web
gate passes formatting, lint, typecheck, 40 unit files/112 tests, and the
production build. Playwright browser smoke passes 36 tests with two intentional
device-conditional skips, including the Strategy Lab registry surface and
accessibility smoke. The control-plane validator, contract validator,
deterministic scenario runner, replay comparison, and `git diff --check` also
pass.

Final state: `PASSED / MULTI_STRATEGY_PRODUCT_READY`. RM-242 is a standalone
product checkpoint and is excluded from Round 4 task counts. No RM-241 frozen
artifact, research candidate, scientific result, cloud call, paid resource, or
production claim changed. Remote GitHub Actions run `33319439637` passed all
five repository jobs for implementation commit
`23c25706b66c36a89b3b7a7ed8890ddd2761943c`; closure run `33319645285` passed
all five jobs for final commit `906f5711dd672cb7aed7c8a066823380a9bb5e89`.
The later documentation-only correction commit `3b8d4f3a02ae38cf720d1de36d5af6a8ab1b3d32`
was checked by run `33319887670`; its only failure was the pre-existing desktop
reconnect smoke expectation for `Stream connected` (the mobile counterpart and
all 35 other browser tests passed). A failed-job rerun reproduced that same
unrelated test; no RM-242 strategy or registry test failed.
