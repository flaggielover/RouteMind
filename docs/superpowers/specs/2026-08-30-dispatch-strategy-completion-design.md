# RouteMind Dispatch Strategy Completion & Integration Design

## Scope

RM-242 is an engineering/product integration checkpoint. It makes existing
dispatch capabilities selectable, replayable, verifiable, observable, and
truthfully visible without changing frozen Product Readiness scenarios or
promoting research mechanisms. The implementation is bounded to deterministic
local compute and existing Java durable-state boundaries.

## Design

- Keep the seven registered dispatch strategies unchanged and add one genuine
  bounded `local-search` strategy to the registry. It improves an initial
  deterministic assignment only within a fixed iteration budget and never
  claims global optimality.
- Keep `vrptw` as the generic VRP capability. Expose existing route insertion
  through an explicit `dynamic-insertion` planner/API that requires a supplied
  immutable active route; missing route state is an explicit incompatibility,
  never a fabricated historical route. Expose existing trigger gating through
  an explicit `dynamic-replanning` API result that preserves the prior-plan
  reference, trigger, selected strategy, and generation.
- Extend `StrategyRegistry` descriptors with capability and parameter metadata,
  while representing insertion/replanning as capability paths rather than
  pretending they are single-request solvers. Unknown names and invalid
  configuration remain rejected; no implicit solver substitution is added.
- Make `ScenarioKernel` strategy selection explicit and capture the actual
  travel-provider fallback result in RM-237 observations. Add a bounded
  comparison helper/CLI that runs compatible strategies independently against
  the same frozen manifest and seed; separate runs never manufacture policy
  switches.
- Make Strategy Lab fetch the registry catalog and use descriptor-driven
  selectors. Comparison remains labeled simulation/replay and exposes only
  common, actually recorded metrics.

## Validation

Focused tests cover local-search determinism and verifier compatibility,
insertion feasibility/tie-breaking/infeasibility, replan provenance, registry
enumeration and invalid configuration, multi-strategy replay/comparison,
fallback propagation, and registry-driven web rendering. Existing Python,
Java, frontend, contract, determinism, solver-verification, control-plane, and
browser gates remain authoritative.

No research results, claims, killed candidates, R3-325 state, paid providers,
cloud resources, or raw external data are changed.
