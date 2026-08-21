# P1 Order Lifecycle State Machine

RM-011 owns the smallest durable order lifecycle needed by the business runtime.
Authentication, payment, dispatch strategy, and courier location remain outside
this task.

## States and transitions

`CREATED -> CONFIRMED -> ASSIGNED -> PICKED_UP -> DELIVERED`

`CREATED`, `CONFIRMED`, and `ASSIGNED` may transition to `CANCELLED`. Every
other transition is rejected, including repeated commands and transitions out
of terminal states. A transition records the actor, command time, source and
target states, and a monotonic sequence number.

## Consistency

The domain aggregate applies one transition at a time and rejects stale
expected versions. The persistence adapter uses an optimistic version column;
the order row and transition history are written in one transaction. A unique
`(order_id, sequence_number)` constraint prevents duplicate audit entries.
