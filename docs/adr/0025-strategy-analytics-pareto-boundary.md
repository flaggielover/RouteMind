# ADR 0025: Strategy Analytics and Pareto Boundary

## Decision

The Strategy route adds a read-only analytics projection over recorded What-if
comparison results. The Web domain computes Pareto membership from the actual
returned metrics: assignment coverage is maximized, while simulated duration,
observed runtime, and scenario-risk index are minimized. A result is on the
frontier when no other recorded result is no worse on every objective and
strictly better on at least one.

Strategy metadata is displayed from the versioned compute registry contract:
maturity, capabilities, parameter defaults and bounds, constraints, the
nearest fallback, and the independent verifier boundary. It is labeled as
registry metadata and does not claim that every strategy was executed in the
current comparison.

## Boundaries

- What-if remains compute-owned and scenario-only; no Java durable state is
  mutated by analytics or Pareto calculation.
- Assignment, duration, runtime, and risk are evidence-backed only when the
  recorded comparison returns them.
- Fairness, cost, completion, overtime, distance, and per-result verification
  remain explicitly unavailable until a producer supplies those fields.
- Pareto status is a comparison aid, not a production policy ranking or causal
  claim. Provenance retains the recorded run, scenario, seed, and claim label.

## Consequences

The UI can show trade-offs without collapsing unlike metrics into a fabricated
score. Extending the metric set requires a versioned producer and an explicit
objective direction before it can affect the frontier.
