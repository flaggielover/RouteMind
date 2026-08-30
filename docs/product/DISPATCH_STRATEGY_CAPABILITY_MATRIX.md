# Dispatch Strategy Capability Matrix

Checkpoint: RM-242 (engineering integration; no research claim)

## Before

| Capability | Implementation | Registry | Parameter schema | Unit-tested | Solver verified | Compute API | Java authoritative flow | Frozen scenarios | Replay | RM-237 | Strategy Lab | Maturity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nearest | yes | yes | yes (empty) | yes | yes | yes | accepts provenance | runner hardcoded nearest | yes | yes | handwritten | BASELINE |
| weighted-greedy | yes | yes | yes | yes | yes | yes (config dropped by execute route) | accepts provenance | runner hardcoded nearest | yes | yes | handwritten | BASELINE |
| hungarian | yes (single-request adapter) | yes | yes (empty) | yes | yes | yes | accepts provenance | runner hardcoded nearest | yes | yes | handwritten | BASELINE |
| risk-aware | yes | yes | yes | yes | yes | yes | accepts provenance | runner hardcoded nearest | yes | yes | handwritten | BASELINE |
| minimum-cost-flow | yes (batch + single adapter) | yes | yes (empty) | yes | yes | yes | accepts provenance | runner hardcoded nearest | yes | yes | handwritten | ENGINEERING |
| partitioned-assignment | yes (partitioned batch) | yes | yes (empty) | yes | yes | yes | accepts provenance | runner hardcoded nearest | yes | yes | handwritten | ENGINEERING |
| vrptw / generic VRP | yes (bounded route planner + single adapter) | yes | yes (empty) | yes | yes | yes | accepts provenance | runner hardcoded nearest | yes | yes | handwritten | BASELINE |
| local-search | no | no | no | no | no | no | no | no | no | no | no | ENGINEERING |
| dynamic-insertion | yes (planner only) | no | no | yes | route verifier | no explicit endpoint | accepts strategy text only | incompatible | planner replayable | no policy path | no | ENGINEERING |
| dynamic-replanning | yes (trigger policy only) | no | no | yes | policy invariants | no explicit endpoint | Java remains authority | incompatible | policy replayable | no policy path | no | ENGINEERING |
| batch / zone dispatch | yes via flow classes | indirect | empty | yes | flow invariants | only RouteBench path | accepts resulting decision | runner single-request only | yes | yes | no | ENGINEERING |

## After

| Capability | Implementation | Registry | Parameter schema | Unit-tested | Solver verified | Compute API | Java authoritative flow | Frozen scenarios | Replay | RM-237 | Strategy Lab | Maturity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nearest | yes | yes | yes (empty) | yes | yes | yes | accepts versioned decision provenance | selectable, fixed run | yes | yes | API-driven | BASELINE |
| weighted-greedy | yes | yes | yes (`distance_weight`) | yes | yes | yes | accepts versioned decision provenance | selectable, fixed run | yes | yes | API-driven | BASELINE |
| hungarian | yes (single-request adapter) | yes | yes (empty) | yes | yes | yes | accepts versioned decision provenance | selectable, fixed run | yes | yes | API-driven | BASELINE |
| risk-aware | yes | yes | yes (five weights) | yes | yes | yes | accepts versioned decision provenance | selectable, fixed run | yes | yes | API-driven | BASELINE |
| minimum-cost-flow | yes (batch + single adapter) | yes | yes (empty) | yes | yes | yes | accepts versioned decision provenance | selectable, fixed run | yes | yes | API-driven | ENGINEERING |
| partitioned-assignment | yes (partitioned batch) | yes | yes (empty) | yes | yes | yes | accepts versioned decision provenance | selectable, fixed run | yes | yes | API-driven | ENGINEERING |
| vrptw / generic VRP | yes (bounded route planner + single adapter) | yes | yes (empty) | yes | yes | yes | accepts versioned decision provenance | selectable, fixed run | yes | yes | API-driven | BASELINE |
| local-search | yes (bounded first-improvement pair swaps) | yes | yes (`max_iterations`, 1..256) | yes | yes | yes | accepts versioned decision provenance | selectable, fixed run | yes | yes | API-driven | ENGINEERING |
| dynamic-insertion | yes (immutable route planner) | explicit capability endpoint; not a single-request solver | route-state payload | yes | route verifier | `/api/v1/dispatch/insertion` | compute proposal; Java remains durable owner | explicit route state only | yes | provenance fields available | surfaced as non-solver capability | ENGINEERING |
| dynamic-replanning | yes (bounded trigger policy) | explicit capability endpoint; not a single-request solver | debounce/cooldown | yes | policy invariants | `/api/v1/dispatch/replan` | compute proposal requires Java validation | explicit trigger state only | yes | provenance fields available | surfaced as non-solver capability | ENGINEERING |
| batch / zone dispatch | yes via flow classes | flow strategies selectable | empty | yes | flow invariants | RouteBench/strategy execution | resulting decision is Java-authoritative | fixed scenarios use compatible single-request projections | yes | yes | API-driven | ENGINEERING |

All registry strategies are selected by name with no implicit substitution. The
business API records the selected strategy/version and remains the durable
assignment authority; Python owns strategy execution and verification. Research
only RADS variants, Spatial Lock-In, Policy Boundary Learning, and
Self-Calibrating Twin mechanisms remain outside the product list.
