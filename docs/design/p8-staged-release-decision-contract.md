# P8 Staged Release and Rollback Decision Contract

## Goal

Make staged traffic decisions auditable and deterministic while keeping the
active strategy and durable business state authoritative in the existing
runtime. The contract evaluates recorded observations; it does not switch
traffic, mutate deployment state, or restore a service.

## Stage plan invariants

`StagePlan` binds an active release digest, candidate release digest, rollback
package digest, policy version, and an ordered sequence of stages. Each stage
has a unique identifier, a positive traffic allocation in basis points, a
minimum observation count, a soak duration, bounded error/regression limits,
and the health checks required before promotion. Allocations are strictly
increasing and end at 10,000 basis points; the candidate digest and rollback
digest must be content-addressed and must not be mutable tags.

The plan is append-only input to evaluation. A stage observation records the
stage identifier, sample count, error rate, regression rate, disagreement rate,
health-check status, and rollback readiness. Values are normalized into integer
basis points/counts before comparison so equivalent inputs produce the same
decision digest.

## Decision policy

`evaluate_stage()` returns one of `promote`, `hold`, or `rollback` with stable
reason codes and a content-derived digest:

- `rollback` wins whenever rollback readiness is false, a required health check
  is unhealthy, or a configured error/regression/disagreement limit is met or
  exceeded;
- `hold` applies when safety limits are clear but minimum samples or soak time
  are incomplete;
- `promote` requires all safety checks, minimum observations, and soak duration,
  and advances only to the next declared stage.

An observation cannot authorize promotion beyond the plan's next stage, and a
rollback decision never executes recovery. This preserves the active release's
operational authority and makes traffic control an explicit external gate.

## Validation boundary

Tests will cover canonical ordering, allocation and digest invariants,
promotion/hold/rollback precedence, threshold boundaries, missing health checks,
and read-only behavior. Deployment controllers, service-mesh traffic shifting,
registry signatures, live monitoring, and production rollback execution remain
external capabilities.
