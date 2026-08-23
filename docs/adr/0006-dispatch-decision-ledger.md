# ADR-0006: Durable Dispatch Decision Ledger

## Context

Dispatch output can be replayed, compared, or investigated after the request that
produced it is gone. The existing assignment audit proves the Java state transition,
but it does not preserve the canonical compute inputs and outputs or identify the
reference data and clock semantics used by the decision.

## Decision

Java records one bounded decision ledger row in the same assignment transaction.
`decision_id` is the stable compute request identifier and is unique; a conflicting
reuse is rejected while an identical retry is idempotent. The ledger stores strategy
and version, reference-data identity, explicit `WALL` clock domain, original compute
input/output digests, canonical JSON input/output snapshots, and independent
content-addressed snapshot digests. Snapshots are capped at 64 KiB each and are
indexed by order for investigation. The assignment outbox remains a compact hot-path
event; the ledger is the durable provenance source for extended inspection.

## Consequences

The ledger is PostgreSQL-backed and Java-owned, so it remains available when Redis or
external object storage is unavailable. A later archival worker can move larger
research payloads behind these digests without changing assignment authority or the
v1 dispatch contract. Python continues to own computation; it supplies the digests
and strategy metadata, while Java records what was actually committed.
