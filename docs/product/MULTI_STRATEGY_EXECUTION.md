# Multi-Strategy Execution

RM-242 provides one deterministic execution path from strategy selection through
compute verification, scenario replay, RM-237 observation, and Strategy Lab.

## Fixed-strategy comparison

`ScenarioKernel` accepts an explicit strategy name and configuration. The
`compare_strategies` helper runs each selected name independently against the
same immutable `ScenarioManifest` and seed. It returns successful runs plus an
explicit incompatibility/failure record for any name that cannot execute. A
comparison never compares wall-clock latency inside a replay digest and never
turns separate runs into policy switches. RM-237 switch, dwell, occupancy, and
transition metrics therefore remain scoped to one execution path.

The deterministic scenario CLI supports both `--strategy NAME` and
`--compare NAME[,NAME...]`. The existing RouteBench API accepts up to sixteen
selected strategies. Each result records strategy/version, assigned couriers,
feasibility, replay digest, fallback states, selection mode, decision
provenance, and unavailable semantics for degradation or route-estimate fields
that the current scenario model cannot observe.

## Engineering capability paths

`partitioned-assignment` is the existing bounded batch/zone orchestration. It
filters candidates by request partition and delegates to the existing flow
solver; no alias strategy is introduced. `vrptw` is the existing generic VRP
capability for bounded stops, vehicles, capacity, and time windows.

Dynamic insertion is an explicit `/api/v1/dispatch/insertion` request with a
supplied immutable active route. It returns a new route, feasibility reason,
incremental travel, prior-plan reference, result reference, input/output
digests, and a replay digest without mutating the supplied route or inventing
history.

Dynamic replanning is an explicit `/api/v1/dispatch/replan` proposal. It
preserves the trigger, previous plan reference, triggering state, selected
strategy, resulting-plan reference when supplied, generation, and replay
digest. It is never a durable assignment operation; Java must validate and
apply any resulting business state.

## Adaptive switching boundary

The repository now supports fixed-strategy comparisons and replayable
observations for arbitrary registered engineering strategy names. It does not
contain a legitimate product path that changes strategy over time during one
execution. RM-237 switching metrics remain zero unless a future product control
path actually selects a different strategy within one run. Research selectors
are not used to manufacture such a path.
