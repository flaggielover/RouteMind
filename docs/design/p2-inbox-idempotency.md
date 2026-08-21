# P2 Inbox and Idempotent Consumer Semantics

RM-021 makes event consumption durable before any broker acknowledgement.

An event ID is the deduplication key. A new event is recorded as `RECEIVED`,
claimed as `PROCESSING`, and marked `PROCESSED` only after the handler finishes.
Duplicates of a processed event are ignored and acknowledged without invoking
the handler again. Failures increment attempts with bounded backoff; after the
configured poison threshold the row becomes `DEAD_LETTER` with a diagnostic
reason and is eligible for operator inspection/replay.

The acknowledgement port is called only after the durable state change, so a
crash before acknowledgement causes redelivery while preserving one logical
effect.
