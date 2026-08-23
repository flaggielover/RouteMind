# ADR-0014: Fulfillment Saga Exception Boundary

Date: 2026-08-23
Status: Accepted

## Context

The order aggregate had the happy path and cancellation, while assignment
timeout, courier rejection, reassignment, and compensation were represented only
as implicit failures. A committed assignment lease could therefore remain active
when the order entered an exceptional terminal path.

## Decision

Keep the saga in the Java business runtime. Add explicit order states for
assignment timeout, assignment rejection, reassignment pending, compensating, and
compensated. The application command service calls a coordinator in the same
transaction; exceptional assignment paths release at most one committed lease
for the order and retain append-only lease evidence. Existing idempotency keys,
optimistic versions, transition audit rows, and Outbox events remain the command
boundary. Payment processing is outside this saga and is not modeled.

## Consequences

Clients can distinguish retryable dispatch exceptions from compensation progress
without inferring them from generic HTTP failures. Reassignment is explicit and
can return to `ASSIGNED` only through a dispatch command. Drift detection remains
useful for pre-existing data or independently injected corruption; the new path
prevents that drift for commands using the Java boundary. The explicit state list
must be kept compatible in Web projections and event consumers.
