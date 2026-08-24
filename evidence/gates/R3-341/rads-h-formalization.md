# R3-341 RADS-H Hysteresis Formalization

Date: 2026-08-25 (Asia/Shanghai)
Status: passed as a formal mechanism contract
Implementation checkpoint: `d33662a9dac967f2f46598d41557e81cc2293497`
GitHub Actions: PASS - run `32756793168` (all five jobs)

## Frozen mechanism plan

The machine-readable plan is
`docs/research/r3/manifests/rads/r3-341-rads-h-formalization-v1.json`.
Its canonical digest is
`4b846bc8b971df269c1c6439b325ab61b7803a83812ced39b352f519acb929c5` and its
byte SHA-256 is
`091a196bfbcaae57077cd862b87a30d7793300bae219f0b6c32e95cff6060e94`.
It references `RADS-BASELINE-v1` and content-addresses the RADS source,
baseline freeze, and hysteresis implementation artifacts.

## Explicit state and transitions

- Parameters are frozen as enter threshold `0.05`, exit threshold `0.02`,
  persistence `2` consecutive pressure ticks, minimum dwell `3` ticks, and
  switching cost `0.01` objective units.
- State is `(active_strategy, regime_id, pressure_ticks, dwell_ticks,
  switch_count)`. A regime change resets pressure and dwell and emits `hold`;
  pressure is never carried across regime identities.
- Relative candidate advantage is
  `(current_score-candidate_score)/max(abs(current_score),1e-12)`.
  A switch requires advantage at least the enter threshold, minimum dwell, and
  the persistence count. A candidate below the enter threshold or outside the
  negative exit band resets pressure and holds.
- A switch emits a proposal, applies the frozen switching cost for accounting,
  resets pressure/dwell, and increments switch count. The policy never applies
  assignments or owns durable state.
- A simple cooldown is explicitly separate: it is minimum dwell without a
  pressure threshold or persistence and is a comparator, not RADS-H.

## Executable evidence

- The immutable state machine covers regime reset, active-strategy hold,
  minimum-dwell hold, exit-band hold, below-enter hold, persistence hold, and
  switch transitions. Objective scores must be finite; malformed state/config
  values fail closed.
- Six plan tests and three mechanism tests pass; both R3-341 modules reach 100%
  statement and branch coverage.
- `./scripts/compute-api.ps1 -Action check`: PASS - 846/846 Python tests,
  95.86% total coverage, Ruff and strict mypy, 6 schemas/18 fixtures,
  determinism, analytics, semantic metrics, and repository controls.
- GitHub Actions run `32756793168`: PASS for Java, Python/contracts,
  Web/browser smoke, control-plane/Compose, and bounded degradation/resilience.

## Final disposition

R3-341 closes `E-PASS / X-NOT-REQUIRED / S-NOT-APPLICABLE / C-DEFERRED`.
This is a preregistered mechanism boundary before R3-342 experiments. It does
not establish empirical stability, switching reduction, service non-inferiority,
cost bounds, safety, novelty, or performance.
