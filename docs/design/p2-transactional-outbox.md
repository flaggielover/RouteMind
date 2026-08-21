# P2 Transactional Outbox Publishing

RM-020 connects the Java business transaction boundary to the versioned event
envelope without a dual-write claim.

## Atomic write

`OrderCommandService` loads and transitions an order, writes the aggregate, and
inserts one pending `OutboxMessage` inside the same Spring transaction. A
transaction rollback therefore leaves neither a changed order nor an orphaned
event.

## Relay contract

`OutboxRelay` claims due pending/retryable rows, publishes the original envelope
with its stable event ID, and marks the row published only after publisher
confirmation. A failed publish increments the attempt count and schedules a
bounded exponential delay. The row remains durable across process restart and
can be retried without creating a second logical event.

## Storage

Flyway V4 owns `outbox_messages`. Event identity, aggregate identity/version,
correlation, causation, trace, payload, retry state, and timestamps are stored
explicitly. A unique event ID prevents duplicate logical records.
