# ADR-0015: Sequenced Courier Location History

Date: 2026-08-23
Status: Accepted

## Context

Courier location reports arrive through a realtime path and can be duplicated,
delayed, or observed after a newer report. The current location must remain a
rebuildable hot projection while operational consumers still need bounded
durable evidence of the reports that advanced it.

## Decision

Java remains authoritative for accepted courier location state. Every report
carries a positive courier-scoped sequence, observed event time, server
ingestion time, and online state. PostgreSQL keeps the latest accepted report
and a bounded history of the most recent 128 sequences per courier; a report
with an equal or lower sequence is not allowed to overwrite current state or
create another history row. Redis GEO remains the hot spatial projection and
is updated only after the durable state advances. Outbox events include the
sequence and both timestamps so SSE and dispatch consumers can reject stale
events independently of arrival order.

## Consequences

Operators can distinguish event-time lag, ingestion delay, offline state, and
stale projection without treating Redis as durable truth. History is sufficient
for bounded audit and recovery checks but intentionally does not become an
unlimited trajectory store. Integrity/anomaly analysis remains a later,
read-oriented capability and cannot silently discipline a courier.
