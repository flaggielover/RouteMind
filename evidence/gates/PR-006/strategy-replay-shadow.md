# PR-006 Scenario, Replay, and Shadow Control Surface

Status: implemented locally; simulation/replay authority remains explicit.

Digital Twin scenario selection is constrained to the eight frozen manifest IDs:
`NORMAL_BASELINE`, `DINNER_RUSH`, `COURIER_SHORTAGE`, `MERCHANT_DELAY`,
`TRAFFIC_DEGRADATION`, `ROUTING_PROVIDER_FAILURE`, `DISPATCH_PRESSURE`, and
`RECOVERY`. Each option is labeled `SIMULATION`; an existing non-catalog state is
retained as a current value rather than silently rewritten.

Strategy Lab exposes the active strategy/version, recorded assignment signal,
verified replay artifact state when present, and an explicit shadow status. Replay
and what-if controls retain fail-closed verification and non-causal labels. No
production strategy claim or scientific claim changed.

Verification: scenario control and live-boundary focused tests passed; full web
lint/typecheck/build and serial Vitest 39 files / 108 tests passed.

Terminal CI evidence: GitHub Actions run `33305890726` completed successfully;
the role-aware browser smoke gate passed with 34 tests and 2 intentional skips.
