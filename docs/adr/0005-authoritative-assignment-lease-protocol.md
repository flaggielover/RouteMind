# ADR-0005: Authoritative Assignment Lease Protocol

## Context

Dispatch computation can produce more than one decision for the same courier while
messages are delayed, duplicated, or retried. Order optimistic locking alone does
not serialize two different orders competing for one courier.

## Decision

Java owns a PostgreSQL-backed current lease row keyed by `courier_id`. A lease has
`lease_id`, `order_id`, `decision_id`, a monotonically increasing `generation`,
creation/expiry timestamps, and an explicit state. `PROVISIONALLY_RESERVED` leases
are bounded to 30 seconds by the application clock. A pessimistic row lock serializes
reserve/commit/release/expiry transitions; a new reservation can only replace an
expired or released generation. A committed lease remains authoritative until a
separate compensation workflow exists.

Every transition is appended to `dispatch_assignment_lease_events`. The assignment
audit stores the committed lease identifier and generation, and the outbox payload
contains the same values. Redis can cache or accelerate lookup later, but it is not
part of correctness.

Duplicate commit for the same lease and generation is idempotent. A stale generation,
decision mismatch, active competing reservation, committed courier, or expired lease
is rejected. The assignment and lease commit are in one Spring transaction, so an
order transition failure rolls the lease reservation back. Expiry and release are
explicit auditable recovery operations rather than silent deletion.

## Consequences

The current lease table is intentionally one row per courier, which gives a simple
database-enforced serialization point. Historical transitions are append-only and
can support recovery and incident reconstruction. A future scheduler or courier
acknowledgement workflow can call the existing expiry/release repository operations
without changing the authority boundary.
