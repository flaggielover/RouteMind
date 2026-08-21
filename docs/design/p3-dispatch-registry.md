# P3 Dispatch Strategy Registry

RM-030 keeps dispatch computation stateless and comparison-friendly. Strategies
share the immutable `DispatchProblem` / `DispatchDecision` contract, expose a
stable name and version, and are selected through `StrategyRegistry` rather than
hard-coded in an endpoint.

`NearestStrategy` uses Haversine distance in kilometres. Ranking is the tuple
`(distance_km, courier_id)`, so equal-distance candidates produce the same
decision regardless of input order. Empty candidate sets return an explicit
unassigned decision.

The registry measures solve latency with a monotonic clock and records candidate
count and assignment status in decision metadata. This metadata is diagnostic;
it does not become durable business state. Later strategies can be registered
and benchmarked through the same interface without changing the baseline.
